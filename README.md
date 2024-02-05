# MoneyPrinter

Create YouTube Shorts without any effort, simply by providing a video topic to talk about.

## Installation

```bash
git clone https://github.com/FujiwaraChoki/MoneyPrinter.git
cd MoneyPrinter

# Install requirements
pip install -r requirements.txt

# Copy .env.example and fill out values
cp .env.example .env

# Run the backend server
cd Backend
python main.py

# Run the frontend server
cd ../Frontend
python -m http.server 3000
```

See [`.env.example`](.env.example) for the required environment variables.

If you need help, open [ENV.md](ENV.md) for more information.

## Usage

1. Copy the `.env.example` file to `.env` and fill in the required values
1. Open `http://localhost:3000` in your browser
1. Enter a topic to talk about
1. Click on the "Generate" button
1. Wait for the video to be generated
1. The video's location is `temp/output.mp4`

## Fonts

Add your fonts to the `fonts/` folder, and load them by specifiying the font name on line `124` in `Backend/video.py`.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

See [`LICENSE`](LICENSE) file for more information.
