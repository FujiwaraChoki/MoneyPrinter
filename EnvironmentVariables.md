
# Environment Variables

## Required

- TIKTOK_SESSION_ID: Your TikTok session ID is required. Obtain it by logging into TikTok in your browser and copying the value of the `sessionid` cookie.

    - To get the session ID, open TikTok in your browser, log in, and open the developer console. Go to the `Application` tab, and under `Session storage`, copy the value of the `sessionid` .

    - If you are using Chrome or edge, you can also get the session ID by going to 
    `chrome://settings/cookies/detail?site=tiktok.com`
     and copying the value of the `sessionid` cookie.

#### NOTE: 
- The session ID is only valid for a few hours, so you will need to update it regularly.
#### To get the session ID in India
- if you are from India change the region other than india using vpn  in the TikTok website and then get the session ID .


- IMAGEMAGICK_BINARY: The filepath to the ImageMagick binary (.exe file) is needed. Obtain it [here](https://imagemagick.org/script/download.php)

- For Windows, the default path is 
     - `C:\Program Files\ImageMagick-7.0.11-Q16-HDRI\magick.exe`

- PEXELS_API_KEY: Your unique Pexels API key is required. Obtain yours [here](https://www.pexels.com/api/)

     - create an account in pexels and then go to the api key section and get the api key.The Pexels API key is used to download images from Pexels.

## Optional
 
- OPENAI_API_KEY: Your unique OpenAI API key is required. Obtain yours [here](https://platform.openai.com/api-keys), only nessecary if you want to use the OpenAI models.

- GOOGLE_API_KEY: Your Gemini API key is essential for Gemini Pro Model. Generate one securely at [Get API key | Google AI Studio](https://makersuite.google.com/app/apikey)

* ASSEMBLY_AI_API_KEY: Your unique AssemblyAI API key is required. You can obtain one [here](https://www.assemblyai.com/app/). This field is optional; if left empty, the subtitle will be created based on the generated script. Subtitles can also be created locally.

Join the [Discord](https://dsc.gg/fuji-community) for support and updates.
