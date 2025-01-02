from argparse import ArgumentParser
from renderer import render
from utils import print_banner

def main():
    parser = ArgumentParser(description='Movie Maker Renderer: Render Windows Movie Maker projects with arbitrary output formats (e.g. HD, Full HD, 2K, 4K, etc.)')
    parser.add_argument('-p', '--project', type=str, required=True, help='Path to the Windows Movie Maker project file (.wlmp)')
    parser.add_argument('-o', '--output', type=str, required=True, help='Path to the output file. The video codec in inferred from the file extension. Program will ask before overwriting existing file (except when setting --overwrite-existing)')
    parser.add_argument('--overwrite-existing-file', type=bool, default=False, help='Explicitly overwrites any preexisting output file with the same name without asking. Useful for batch processing. ')
    parser.add_argument('--width', type=int, default=3840, help='Width of the render output in pixels (default: 3840)')
    parser.add_argument('--height', type=int, default=2160, help='Height of the render output in pixels (default: 2160)')
    parser.add_argument('--fps', type=int, default=30, help='FPS (frames per second) of the render output (default: 30)')
    args = parser.parse_args()
    print_banner()
    render(args.project, args.output, args.width, args.height, args.fps, args.overwrite_existing_file)

if __name__ == '__main__':
    main()
