# Gfriends Inputer One Click Import Tool
Media server avatar import tool for Emby/Jellyfin, [Gfriends Girlfriend Avatar Repository](https://github.com/gfriends/gfriends) spin-off project.
> *There is no correlation between this repo and Korean girl group GFRIEND.*

## Catalog
* [Quick Start](# Quick Start)
* [Advanced Description](# Advanced description)
   * [Use AI to precisely crop avatars](# Precisely crop avatars)
   * [Scrape actor's personal information](# Scrape actor's personal information)
   * [Timed Auto-run](# Timed auto-run)
   * [Import Local Avatars](# Import Local Avatars)
   * [Custom avatar source](# Custom avatar source)
   * [Third-party scraping tool](# Third-party scraping tool)
* [License and legal information](# License and legal information)

## Quick Start
#### 1. Download and decompress
Please download and unzip the Gfriends Inputer program zip file at [Release](https://github.com/gfriends/gfriends-inputer/releases). <br>
*Hint: The program can connect to **remote** media servers, so please choose the system that you are comfortable with. *

#### 2. Get Media Server API key
Go to the Emby / Jellyfin console, `Advanced` - `API Key` - `New API Key` and follow the prompts to generate an API key.

#### 3. Edit the configuration file and run
**Mac / Windows users** run the executable program `Gfriends Inputer.exe` directly <br>
**Linux User** Open command terminal: run `chmod +x "Gfriends Inputer"` to grant permissions, then execute `./"Gfriends Inputer"` to start the program

The first time the program is run, the configuration file `Config.ini` is automatically generated, and the required fields in the configuration file are `Address of the media server` and `API Key` Obtained.

*Hint: V2.x older versions of Mac/Linux configuration files are in the user root directory, commonly found in: `/Users/username/`,`/home/username/`,`/root/`*

```
CLI command: "Gfriends Inputer" [-h] [-c [CONFIG]] [-q] [-v]

Option Description.
-c [CONFIG], --config   [CONFIG]
                        Specify the configuration file path, the default is the running directory.
-h, --help              Show this help information.
-q, --quiet             Turn on silent mode, no messages will be printed.
--skip-update           Skips the update check and forces the old version to run.
--debug                 Export debug logs even if the configuration file is not enabled in debug mode.
-v, --version           Show current version.
```

You can also run the source code directly in Python 3.6 and above
```
git clone https://github.com/gfriends/gfriends-inputer.git
cd ./gfriends-inputer
pip install -r requirements.txt
python3 "./Gfriends Inputer.py"
```

## Advanced Instructions

Completing advanced configurations on-demand helps enhance the experience.

### [Precise cropping of avatars

The headshots in the repository may not be the standard size and the media server may automatically stretch the headshots to distort them, which requires cropping them. This is rarely the case, but to avoid cropping to the actor's face, you should configure AI precision cropping.

**1. OpenCV DNN AI**<br>
*Gfriends Inputer v3.0 and subsequent versions supported*

Enabled by default, no configuration required. [Opencv](https://opencv.org/) provides local, non-sensitive face recognition with accuracy and speed without networking.

**2. Baidu AI**<br>
*Gfriends Inputer v2.7 and subsequent versions support*

> *This service requires real-name authentication with a mainland Chinese resident ID and an understanding that you agree to the [Service Agreement](https://cloud.baidu.com/doc/Agreements/s/yjwvy1x03), [Privacy Policy](https://cloud.baidu.com/doc/) of the Baidu Intelligent Cloud and the [Service Agreement](https://cloud.baidu.com/doc/Agreements/s/yjwvy1x03) of the Baidu AI Open Platform. Agreements/s/Kjwvy245m) and the [Service Agreement](https://ai.baidu.com/ai-doc/Reference/kk3dwjg7d) of Baidu AI Open Platform. *

You can apply for the relevant API in the following ways:
1. Visit https://ai.baidu.com Baidu AI Open Platform, log in and access the console.
2. Go to "Body Analysis" - "Create Application", fill out the form as required and check the "Body Analysis " Interface.
3. Go to `Body Analysis` - `Manage Applications`, get `BD_App_ID`, `bd_api_key`, `bd_secret_ Key`, and edit the `Baidu AI API` section in the configuration file.

### [Scraping Actor's Personal Information
*Gfriends Inputer v3.0 and subsequent versions supported*

It only needs to be turned on in the configuration file. The program will download the avatar and incidentally search for your girlfriend's personal information (birthday, Circumference, Height, Etc.) and import it to the server along with it.

### [Timed Auto Run
*Gfriends Inputer v2.6 and subsequent versions support*

After the first run has been tested without errors, you can write commands to a Crontab task to run the program in the background at regular intervals.

```
# Run at zero every day, no log output
0 0 * * * * "/home/user/gfriends Inputer"
# Monday zero runs, outputs logs, and specifies profile path
0 0 * * 0 "/home/user/gfriends Inputer" -q -c "/home/user/config.ini"
```

### [Import local avatar
*Gfriends Inputer v2.5 and subsequent versions support*

The `Avatar` folder is automatically created when the program is first started (you can change it in the configuration file). Rename the local avatar image to `ActorName.jpg` or move a third-party avatar package to this folder. After that, the import tool will prefer to find and import avatars from this folder, while those that do not exist in the local path will try to search and import from the Gfriends repository.

### [Custom avatar source

In the repository, multiple avatars of the same girlfriend from different sources may be included. In this case, by default, the avatars are automatically selected based on the quality and size of the avatars and then imported. <br>
However, everyone has different preferences. For example, some people may not like Graphis avatars because they have their girlfriend's name marked on them. Some may not like EBODY's avatar because the girlfriend's clothes are too revealing.

**1. Manually select an avatar**<br>
*Gfriends Inputer v3.0 and subsequent versions supported*

Only need to be turned on in the configuration file. When the program encounters multiple avatars, it automatically downloads all the avatars of the corresponding actors, and you can manually delete the ones you don't like.

**2. Factory Blacklist**<br>
*Gfriends Inputer v2.x Support*

Edit the `label Blacklist` in the configuration file and fill in the labels so that the corresponding avatars will not be acquired. The specific label name can be found in the main repository [Image Source](https://github.com/gfriends/gfriends#%e5%9b%be%e7%89%87%e6%9d%a5%e6%ba%90) or [`Content`](https://github.com/ gfriends/gfriends/tree/master/Content) directory.

### [Third-party scraping tool]
It is recommended to pair with Gfriends Inputer for scraping and organizing projects, a powerful tool to help you get more done with less effort.

[Movie Data Capture](https://github.com/yoshiko2/AV_Data_Capture "AV Data Capture"): local movie metadata scraper. <br>
Derivative projects: [AVDC GUI](https://github.com/moyy996/AVDC "AVDC Gui"), [MDCx](https://github.com/anyabc/something "MDCx")

[JavScraper](https://github.com/JavScraper/Emby.Plugins.JavScraper "javscraper"): a Japanese movie scraper plugin for Jellyfin/Emby that grabs movie information from certain websites.

[Javtube](https://github.com/javtube/jellyfin-plugin-javtube "javtube"): another superb JAV plugin developed for Jellyfin/Emby. (partially open source)

[JAVSDT](https://github.com/junerain123/javsdt "javsdt"): Japanese Film Standardization Tool. (closed source)

[JAVOneStop](https://github.com/ddd354/JAVOneStop "javonestop"): One-stop JAV, All-in-One's JAV processing tool.

*Do you know of other similar open source tools? Feel free to submit issues and let me know. *

## Licensing and Legal Information
This project is licensed under the [MIT](https://github.com/gfriends/gfriends-inputer/blob/main/LICENSE) License, in addition to:

1. The project is only for technical and academic exchange, and is strictly prohibited for commercial and other profit-making purposes.
2. Please consciously comply with local laws and regulations, all consequences arising from the user's own responsibility.
3. The author reserves the right of final decision and final interpretation.

If you do not agree to any of the above terms, please do not use this program directly or indirectly.
