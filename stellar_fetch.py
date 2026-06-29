import os
import re
import sys
import requests
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress

# Initialize Rich Console
console = Console()

# NASA API Configuration
API_KEY = "DEMO_KEY"  # Replace with your own key for higher rate limits
APOD_URL = f"https://api.nasa.gov/planetary/apod?api_key={API_KEY}"

def check_dependencies():
    """Verify required packages are installed."""
    try:
        import requests
        import rich
    except ImportError as e:
        console.print(f"[bold red]❌ Missing required package: {e}[/bold red]")
        console.print("[yellow]Install dependencies with: pip install requests rich[/yellow]")
        sys.exit(1)

def sanitize_filename(title):
    """Sanitize title to create a valid filename."""
    # Remove special characters, keep only alphanumeric, spaces, and hyphens
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces with underscores and convert to lowercase
    sanitized = sanitized.replace(' ', '_').lower()
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Limit length to 200 characters (filesystem safe)
    sanitized = sanitized[:200]
    return sanitized

def fetch_cosmos_data():
    """Fetches today's APOD data from NASA."""
    with console.status("[bold cyan]🔭 Querying the cosmos...", spinner="star"):
        try:
            response = requests.get(APOD_URL, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            console.print("[bold red]❌ Request timed out. NASA servers might be busy.[/bold red]")
            return None
        except requests.exceptions.HTTPError as e:
            console.print(f"[bold red]❌ HTTP Error: {e.response.status_code}[/bold red]")
            if e.response.status_code == 401:
                console.print("[yellow]Check your API key![/yellow]")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]❌ Failed to establish contact with NASA: {e}[/bold red]")
            return None

def download_image(url, title):
    """Downloads the image to the current directory with proper error handling."""
    filename = f"{sanitize_filename(title)}.jpg"
    filepath = Path(filename)
    
    # Check if file already exists
    if filepath.exists():
        console.print(f"[bold yellow]⚠️  File already exists: {filename}[/bold yellow]")
        response = console.input("[cyan]Overwrite? (y/n): [/cyan]").strip().lower()
        if response != 'y':
            console.print("[dim]Download cancelled.[/dim]")
            return
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        with Progress() as progress:
            if total_size > 0:
                task = progress.add_task("[cyan]📥 Downloading image...", total=total_size)
            else:
                task = progress.add_task("[cyan]📥 Downloading image...", total=None)
            
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        if total_size > 0:
                            progress.update(task, advance=len(chunk))
                        else:
                            progress.update(task)
        
        # Format file size for display
        file_size = filepath.stat().st_size
        size_mb = file_size / (1024 * 1024)
        
        console.print(f"\n[bold green]✅ Success![/bold green] Image saved as [bold white]{filename}[/bold white] ({size_mb:.2f} MB)")
        
    except requests.exceptions.Timeout:
        console.print(f"[bold red]❌ Download timed out[/bold red]")
        # Clean up partial file
        if filepath.exists():
            filepath.unlink()
    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]❌ Failed to download image: HTTP {e.response.status_code}[/bold red]")
        if filepath.exists():
            filepath.unlink()
    except OSError as e:
        console.print(f"[bold red]❌ File system error: {e}[/bold red]")
        if filepath.exists():
            filepath.unlink()
    except Exception as e:
        console.print(f"[bold red]❌ Unexpected error: {e}[/bold red]")
        if filepath.exists():
            filepath.unlink()

def main():
    check_dependencies()
    
    console.print("\n[bold magenta]🚀 Welcome to Stellar-Fetch[/bold magenta]\n")
    
    data = fetch_cosmos_data()
    
    if data:
        # Extract data with defaults
        title = data.get('title', 'Unknown Title')
        explanation = data.get('explanation', 'No explanation provided.')
        date = data.get('date', 'Unknown Date')
        copyright_info = data.get('copyright', 'Public Domain')
        media_type = data.get('media_type', 'unknown')
        
        # Create a beautiful panel for the explanation
        title_text = Text(title, style="bold yellow")
        
        panel = Panel(
            explanation,
            title=title_text,
            subtitle="[italic]🌌 NASA Astronomy Picture of the Day[/italic]",
            border_style="cyan",
            padding=(1, 2)
        )
        
        console.print(panel)
        console.print(f"\n[bold blue]📅 Date:[/bold blue] {date}")
        console.print(f"[bold blue]©️  Copyright:[/bold blue] {copyright_info}\n")
        
        if media_type == 'image':
            # Try hdurl first (high resolution), fall back to url
            image_url = data.get('hdurl') or data.get('url')
            
            if image_url:
                download_image(image_url, title)
            else:
                console.print("[bold red]❌ No image URL found in response[/bold red]")
        elif media_type == 'video':
            console.print("[bold yellow]📹 Today's media is a video, not an image.[/bold yellow]")
            video_url = data.get('url')
            if video_url:
                console.print(f"[cyan]Watch it here: {video_url}[/cyan]")
        else:
            console.print(f"[bold yellow]⚠️  Unknown media type: {media_type}[/bold yellow]")

if __name__ == "__main__":
    main()
