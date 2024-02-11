# Environment Variables

## Required
- ASSEMBLY_AI_API_KEY: Your unique AssemblyAI API key is required. You can obtain one [here](https://www.assemblyai.com/app/) This field is optional; if left empty, the subtitle will be created based on the generated script.
    - The AssemblyAI API key is used to generate the subtitle for the video.



- TIKTOK_SESSION_ID: Your TikTok session ID is required. Obtain it by logging into TikTok in your browser and copying the value of the `sessionid` cookie.

    - To get the session ID, open TikTok in your browser, log in, and open the developer console. Go to the `Application` tab, and under `Session storage`, copy the value of the `sessionid` .

    - If you are using Chrome or edge, you can also get the session ID by going to `chrome://settings/cookies/detail?site=tiktok.com` and copying the value of the `sessionid` cookie.

  #### NOTE: 
     - The session ID is only valid for a few hours, so you will need to update it regularly.
  #### To get the session ID in India
     - if you are from India change the region other than india using vpn  in the TikTok website and then get the session ID .


- IMAGEMAGICK_BINARY: The filepath to the ImageMagick binary (.exe file) is needed. Obtain it [here](https://imagemagick.org/script/download.php)

    - For Windows, the default path is
          `C:\Program Files\ImageMagick-7.0.11-Q16-HDRI\magick.exe`

- PEXELS_API_KEY: Your unique Pexels API key is required. Obtain yours [here](https://www.pexels.com/api/)

    - create an account in pexels and then go to the api key section and get the api key.   
    - The Pexels API key is used to download images from Pexels.

- ChatGPT_API_KEY: Your unique ChatGPT API key is required. Obtain yours [here](https://platform.openai.com/)
    - The ChatGPT API key is used to generate the script for the video.
 
- YOUTUBE_CLIENT_SECRET: The filepath to the `client_secret.json` file is required. Obtain it by creating a project inside your Google Cloud Platform -> [GCP](https://console.cloud.google.com/).
    
  

Open an issue if you need help with any of these.
