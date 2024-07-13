# MoneyPrinter 💸

Automate the creation of YouTube Shorts, simply by providing a video topic to talk about.

<a href="https://trendshift.io/repositories/7545" target="_blank"><img src="https://trendshift.io/api/badge/repositories/7545" alt="FujiwaraChoki%2FMoneyPrinter | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

> **Important** Please make sure you look through existing/closed issues before opening your own. If it's just a question, please join our [discord](https://dsc.gg/fuji-community) and ask there.

> **🎥** Watch the video on [YouTube](https://youtu.be/mkZsaDA2JnA?si=pNne3MnluRVkWQbE).

Check out the instructions for the local version [here](Local.md).

## FAQ 🤔

### How do I get the TikTok session ID?

You can obtain your TikTok session ID by logging into TikTok in your browser and copying the value of the `sessionid` cookie.

### My ImageMagick binary is not being detected

Make sure you set your path to the ImageMagick binary correctly in the `.env` file, it should look something like this:

```env
IMAGEMAGICK_BINARY="C:\\Program Files\\ImageMagick-7.1.0-Q16\\magick.exe"
```

Don't forget to use double backslashes (`\\`) in the path, instead of one.

### I can't install `playsound`: Wheel failed to build

If you're having trouble installing `playsound`, you can try installing it using the following command:

```bash
pip install -U wheel
pip install -U playsound
```

If you were not able to find your solution, please ask in the discord or create a new issue, so that the community can help you.

## Donate 🎁

If you like and enjoy `MoneyPrinter`, and would like to donate, you can do that by clicking on the button on the right hand side of the repository. ❤️
You will have your name (and/or logo) added to this repository as a supporter as a sign of appreciation.

## Contributing 🤝

Pull Requests will not be accepted for the time-being.

## Star History 🌟

[![Star History Chart](https://api.star-history.com/svg?repos=FujiwaraChoki/MoneyPrinter&type=Date)](https://star-history.com/#FujiwaraChoki/MoneyPrinter&Date)

## License 📝

See [`LICENSE`](LICENSE) file for more information.
