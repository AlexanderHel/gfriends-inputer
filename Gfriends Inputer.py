# -*- coding:utf-8 -*-
# Gfriends Inputer / Girlfriend avatar warehouse import tool
# Licensed under the MIT license.
# Designed by xinxin8816, many thanks for junerain123, ddd354, moyy996.
version = 'v3.04'
compatible_conf_version = ['v3.00', 'v3.01', 'v3.02', 'v3.03', 'v3.04']

import  requests ,  os ,  io ,  sys ,  time ,  re ,  threading ,  argparse ,  logging 
from alive_progress import alive_bar
from configparser import RawConfigParser
from traceback import format_exc
from functools import reduce
from hashlib import md5
from base64 import b64encode
from json import loads
from lxml import etree
from PIL import Image, ImageFilter
from aip import AipBodyAnalysis


def fix_size(type, path):
    try:
        pic = Image.open(path)
        if pic.mode != "RGB": pic = pic.convert('RGB')  # Some pictures haveP通道, Problems with base64 encoding
        (wf, hf) = pic.size
        if not 2 / 3 - 0.02 <= wf / hf <= 2 / 3 + 0.02:  # Handle only images that will be overstretched
            if type == 1:
                fixed_pic = pic.resize((int(wf), int(3 / 2 * wf)))  # Stretching pictures
                fixed_pic = fixed_pic.filter(ImageFilter.GaussianBlur(radius=50))  # Gaussian smoothing filter
                fixed_pic.paste(pic, (0, int((3 / 2 * wf - hf) / 2)))  # Paste the original image
                fixed_pic.save(path, quality=95)
                logger.debug('Gaussian filter processing success' + path)
            elif type == 2:
                fixed_pic = pic.crop((int(wf / 2 - 1 / 3 * hf), 0, int(wf / 2 + 1 / 3 * hf), int(hf)))  # Pixel midline expansion to both sides
                fixed_pic.save(path, quality=95)
                logger.debug('Common cutting success' + path)
            elif type == 3 or type == 4:
                try:
                    if type == 3:
                        x_nose, y_nose = find_faces(pic)   # Transfer binary RGB image, return nose horizontal and vertical coordinates
                    else:
                        with open(path, 'rb') as fp:
                            x_nose = int(BD_AI_client.bodyAnalysis(fp.read())["person_info"][0]['body_parts']['nose'][
                                             'x'])  # Return to nose horizontal coordinate
                        if BD_VIP == 'No':
                            time.sleep(0.2)  # Free user QPS ≈ 2, excluding network latency and performance loss time, this value can be slightly reduced
                        else:
                            time.sleep(1 / 1.1 * int(BD_VIP))
                    if x_nose + 1 / 3 * hf > wf:  # Determine the position of the nose in the figure as a whole
                        x_left = wf - 2 / 3 * hf  # Take the right side
                    elif x_nose - 1 / 3 * hf < 0:
                        x_left = 0  # Left as the edge
                    else:
                        x_left = x_nose - 1 / 3 * hf  # The nose is the center line and extends to the sides
                    fixed_pic = pic.crop((x_left, 0, x_left + 2 / 3 * hf, hf))
                    fixed_pic.save(path, quality=95)
                    logger.debug('AI Cut out successfully' + path)
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    logger.warning('AI Analysis Failure, 跳过 AI 直接裁剪：' + path)
                    print('!! ' + path + ' AI Analysis Failure, 跳过 AI 直接裁剪')
                    fix_size(2, path)
            else:
                logger.error('The avatar processing function is misconfigured and there is no such option：' + str(type))
                print('× The avatar processing function is misconfigured and there is no such option：' + str(type))
                sys.exit()
        return True
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
    except:
        if 'pic' in vars(): del pic  # Close if the image is already open
        if 'fixed_pic' in vars(): del fixed_pic
        print('!! ' + path + ' Avatar size optimization failed.')
        logger.error(path + 'Avatar size optimization failed：' + format_exc())

        # Create a Failed folder and move the failed avatar into it
        failed_dir = re.sub(r'(.*/)(.*)', r'\1Failed/', path)
        failed_path = re.sub(r'(.*/)(.*)', r'\1Failed/\2', path)
        if not os.path.exists(failed_dir): os.makedirs(failed_dir)
        if os.path.exists(failed_path): os.remove(failed_path)
        os.rename(path, failed_path)
        return False


def asyncc(f):
    def wrapper(*args, **kwargs):
        thr = threading.Thread(target=f, args=args, kwargs=kwargs)
        thr.start()

    return wrapper


# @asyncc
def xslist_search(id, name):
    try:
        # Search
        url = "https://xslist.org/search?lg=zh&query=" + name
        response = session.get(url, timeout=10)
        html = etree.HTML(response.text)
        try:
            detial_url = html.xpath('/html/body/ul/li/h3/a/@href')[0]
            logger.debug(name + 'Search to personal information：' + detial_url)
        except:
            logger.debug(name + 'No personal information found')
            return False

        # Get details page
        response = session.get(detial_url, timeout=10)
        html = etree.HTML(response.text)
        try:
            detail_list = html.xpath('/html/body/div[1]/div[3]/div/p[1]/descendant-or-self::text()')
            detail_dict = {}
            for index, info in enumerate(detail_list):
                info = info.replace(' ', '', 2)  # Delete extra spaces
                if '身高' in info or '国籍' in info:
                    if detail_list[index + 1].split(':')[0] != 'n/a':
                        detail_dict[info.split(':')[0]] = detail_list[index + 1].split(':')[0]
                else:
                    if len(info.split(':')) > 1 and info.split(':')[1] != 'n/a':
                        detail_dict[info.split(':')[0]] = info.split(':')[1]
            logger.debug(name + 'Acquired personal information：' + str(detail_dict))
        except:
            logger.warning(name + 'Failure to resolve personal information, page：' + detial_url)
            return False

        # Processing Output Profile
        detail_info = ''
        cups = ProductionLocations = PremiereDate = ''
        for item in detail_dict.items():
            # Output the field to the corresponding position
            if item[0] == '罩杯':
                cups = item[1]
                pass
            if item[0] == '国籍':
                ProductionLocations = item[1]
            elif item[0] == '出生':
                PremiereDate = item[1].replace("年", "-").replace("月", "-").replace("日", "")
            else:  # The rest of the fields are used as profile content
                detail_info += item[0] + ': ' + item[1] + '<br>'

        # Reorganization Requestjson
        detial_json = {"name": name, "Taglines": ['AV女优'], "Genres": [],
                       "ProviderIds": {"Gfriends": "https://git.io/gfriends"},
                       "Overview": detail_info}
        if ProductionLocations:
            detial_json["ProductionLocations"] = [ProductionLocations]
        if PremiereDate:
            detial_json["PremiereDate"] = PremiereDate
        if cups:
            detial_json["Tags"] = ['AV女优', cups]
        else:
            detial_json["Tags"] = ['AV女优']

        url_post = host_url + 'Items/' + id + '?api_key=' + api_key
        response = session.post(url_post, json=detial_json, proxies=host_proxies)
        logger.debug(name + 'Personal information has been uploaded, return：' + response.text)
        return True
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
    except:
        logger.warning(name + 'Personal information scraping failure：' + format_exc())
        return False


def get_gfriends_map(repository_url):
    rewriteable_word('>> Connect with Gfriends Girlfriend Avatar Warehouse...')

    # Define Variables
    if repository_url == 'Default/': repository_url = 'https://raw.githubusercontent.com/gfriends/gfriends/master/'
    gfriends_template = repository_url + '{}/{}/{}'
    filetree_url = repository_url + 'Filetree.json'

    # Checking the file tree cache
    keep_tree = False
    try:
        if os.path.exists('./Getter/Filetree.json'):
            # Add deflate request to prevent compression from not getting true size
            gfriends_response = session.head(filetree_url, timeout=5,
                                             headers={'Accept-Encoding': 'deflate'})
            if os.path.getsize('./Getter/Filetree.json') == int(gfriends_response.headers['Content-Length']):
                keep_tree = True
    except:
        logger.warning('Failed to check file tree cache：' + format_exc())
        keep_tree = False

    if keep_tree:
        with open('./Getter/Filetree.json', 'r', encoding='utf-8') as json_file:
            if aifix:
                map_json = loads(json_file.read())
            else:
                map_json = loads(json_file.read().replace('AI-Fix-', ''))
        print('√ Use Gfriends Girlfriend Avatar Warehouse Cache')
        logger.info('The repository file tree is not updated and uses caching')
    else:
        try:
            response = session.get(filetree_url, timeout=30)
            # Fix some server-side return header not specifying encoding makes subsequent parsing error
            response.encoding = 'utf-8'
        except requests.exceptions.RequestException:
            logger.error('Connection to Gfriends girlfriend avatar repository timed out:' + format_exc())
            print('x Connection to Gfriends avatar repository timed out, please check network connection \n')
            print('x The network connection is abnormal and retry ' + str(max_retries) + ' times failed')
            print('× Please try to enable global proxy or configure local proxy; if proxy is enabled, please check its availability')
            sys.exit()
        except:
            logger.error('Failed to connect to Gfriends girlfriend avatar repository:' + format_exc())
            print('x Network connection exception and retry ' + str(max_retries) + ' times failed')
            print('x Please try to enable global proxy or configure local proxy; if proxy is enabled, please check its availability')
            sys.exit()
        if response.status_code == 429:
            logger.error('The girlfriend repository returned an error: 429 Requests are too frequent, please try again later')
            print('x The girlfriend repository returned an error: 429 Requests are too frequent, please try again later')
            sys.exit()
        elif response.status_code != 200:
            logger.error('The girlfriend repository returned an error, please check the HTTP status code: ' + str(response.status_code))
            print('x The girlfriend repository returned an error: ' + str(response.status_code))
            sys.exit()

        # Applications AI fixes
        if aifix:
            map_json = loads(response.text)
        else:
            map_json = loads(response.text.replace('AI-Fix-', ''))

        # Write to file tree cache
        with open('./Getter/Filetree.json', "wb") as json_file:
            json_file.write(response.content)
        print('√ Connect Gfriends Girlfriend Avatar Warehouse Success')
        logger.info('Connection to the Gfriends girlfriend avatar repository was successful and has been written to the file tree cache')

    # Generate a dictionary of download addresses
    output = {}

    if Conflict_Proc == 1:
        # Allow multiple avatars, then multiple download addresses are stored in a list, otherwise a single string is stored.
        for second in map_json['Content'].keys():
            for k, v in map_json['Content'][second].items():
                # print(second,k, v)
                if k[:-4] in output:
                    output[k[:-4]].append(gfriends_template.format('Content', second, v))
                    # logger.debug('Parsing avatar addresses, multiple avatars attached：' + k[:-4] + ' -> ' + gfriends_template.format('Content', second, v))
                else:
                    output[k[:-4]] = [gfriends_template.format('Content', second, v)]
                    # logger.debug('Resolve avatar address, add：' + k[:-4] + ' -> ' + gfriends_template.format('Content', second, v))
    else:
        for second in map_json['Content'].keys():
            for k, v in map_json['Content'][second].items():
                output[k[:-4]] = gfriends_template.format('Content', second, v)
                # logger.debug('Resolve avatar address：'+ k[:-4] +' -> ' + gfriends_template.format('Content', second, v))

    logger.info('File tree parsed successfully, stock avatar：' + str(map_json['Information']['TotalNum']))
    print('   Stock avatars：' + str(map_json['Information']['TotalNum']) + ' Pieces\n')
    return output


# @asyncc
def check_avatar(url, actor_name, proc_md5):
    try:
        if actor_name in exist_list:  # Actors without headshots skip detection
            actor_md5 = md5(actor_name.encode('UTF-8')).hexdigest()[12:-12]
            if actor_md5 in inputed_dict:  # Skip detection for actors who have not downloaded
                mtime = re.search(r't=\d+', url)[0].replace('t=', '')
                if inputed_dict[actor_md5] == mtime:
                    del link_dict[actor_name]
                    logger.debug(actor_name + 'Avatar does not need to be updated.')
        proc_log.write(proc_md5 + '\n')
        logger.debug(actor_name + 'Avatar update check successful, need to download new avatar.')
    except:
        logger.warning(actor_name + 'Avatar update check failed：' + format_exc())
        print('!! ' + actor_name + ' Avatar update check failed.')


@asyncc
def download_avatar(url, actor_name, proc_md5):
    if type(url) == list:
        urls = url
        i = 1
        for url in urls:
            gfriends_response = session.get(url)
            pic_path = download_path + actor_name + "-" + str(i) + ".jpg"
            if gfriends_response.status_code == 429:
                logger.warning(pic_path + ' Download failed, girlfriend repository returned: 429 Request too fast, please try again later')
                print('!! ' + pic_path + ' Download failed, girlfriend repository returned: 429 Request too fast, please try again later')
                return False
            try:
                Image.open(io.BytesIO(gfriends_response.content)).verify()  # Calibrate downloaded images
            except:
                logger.warning(pic_path + ' Checksum failure, the downloaded avatar may be incomplete')
                print('!! ' + pic_path + ' Checksum failure, the downloaded avatar may be incomplete')
            with open(pic_path, "wb") as code:
                code.write(gfriends_response.content)
            logger.debug(pic_path + ' Download successful')
            i += 1
    else:
        gfriends_response = session.get(url)
        pic_path = download_path + actor_name + ".jpg"
        if gfriends_response.status_code == 429:
            logger.warning(pic_path + ' Download failed, Girlfriend Warehouse return: 429 Request too fast, please try again later')
            print('!! ' + pic_path + ' Download failed, Girlfriend Warehouse return: 429 Request too fast, please try again later')
            return False
        try:
            Image.open(io.BytesIO(gfriends_response.content)).verify()  # Calibrate downloaded images
        except:
            logger.warning(pic_path + ' Checksum failure, the downloaded avatar may be incomplete')
            print('!! ' + pic_path + ' Checksum failure, the downloaded avatar may be incomplete.')
        with open(pic_path, "wb") as code:
            code.write(gfriends_response.content)
        logger.debug(pic_path + ' Download successful')
        actor_md5 = md5(actor_name.encode('UTF-8')).hexdigest()[12:-12]
        mtime = re.search(r't=\d+', url)[0].replace('t=', '')
        inputed_dict[actor_md5] = mtime  # Write to image version log
        proc_log.write(proc_md5 + '\n')


@asyncc
def input_avatar(url, data):
    try:
        session.post(url, proxies=host_proxies, data=data, headers={"Content-Type": 'image/jpeg'})
        logger.debug(url.replace(host_url, '').replace(api_key, '***') + ' Imported successfully.')
    except:
        logger.warning(url.replace(host_url, '').replace(api_key, '***') + ' Import failure.' + format_exc())
        print('!! ' + url.replace(host_url, '').replace(api_key,
                                                        '***') + ' The import failed, probably because the connection to the media server is unstable, please try to reduce the number of import threads.')


@asyncc
def del_avatar(id, name):
    url_post_img = host_url + 'Items/' + id + '/Images/Primary?api_key=' + api_key
    session.delete(url=url_post_img, proxies=host_proxies)
    url_post_img = host_url + 'Items/' + id + '/Images/Backdrop?api_key=' + api_key
    session.delete(url=url_post_img, proxies=host_proxies)
    url_post_img = host_url + 'Items/' + id + '/Images/Thumb?api_key=' + api_key
    session.delete(url=url_post_img, proxies=host_proxies)
    # Reorganization Requestjson
    detial_json = {
        "Name": name,
        "ForcedSortName": name,
        "SortName": name,
        "ChannelNumber": "",
        "OriginalTitle": "",
        "CommunityRating": "",
        "CriticRating": "",
        "IndexNumber": "0",
        "ParentIndexNumber": "0",
        "SortParentIndexNumber": "",
        "SortIndexNumber": "",
        "DisplayOrder": "",
        "Album": "",
        "AlbumArtists": [],
        "ArtistItems": [],
        "Overview": "",
        "Status": "",
        "Genres": [],
        "Tags": [],
        "TagItems": [],
        "Studios": [],
        "DateCreated": "",
        "EndDate": "",
        "ProductionYear": "",
        "Video3DFormat": "",
        "OfficialRating": "",
        "CustomRating": "",
        "ProviderIds": {},
        "PreferredMetadataLanguage": "",
        "PreferredMetadataCountryCode": "",
        "ProductionLocations": [],
        "Taglines": []
    }
    url_post = host_url + 'Items/' + id + '?api_key=' + api_key
    session.post(url_post, json=detial_json, proxies=host_proxies)


def get_gfriends_link(name):
    if name in gfriends_map:
        output = gfriends_map[name]
        logger.debug(name + ' Resolve to avatar address：' + str(output))
        return output
    else:
        logger.debug(name + ' Not resolved to avatar')
        return None


def argparse_function(ver: str) -> [str, str, bool]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default='config.ini', nargs='?', help="The config file Path.")
    parser.add_argument("-q", "--quiet", dest='quietflag', action="store_true",
                        help="Assume Yes on all queries and Print logs to file.")
    parser.add_argument("--skip-update", dest='updateflag', action="store_false",
                        help="Skip update check and try to exec old version.")
    parser.add_argument("--debug", dest='debugflag', action="store_true",
                        help="Debug log, same as debug option in config.")
    parser.add_argument("-v", "--version", action="version", version=ver)
    args = parser.parse_args()
    return args.config, args.quietflag, args.updateflag, args.debugflag


def read_config(config_file):
    global config_settings
    rewriteable_word('>> Read configuration...')
    if os.path.exists(config_file):
        config_settings = RawConfigParser()
        try:
            config_settings.read('config.ini', encoding='UTF-8-SIG')  # UTF-8-SIG Windows Notepad adaptation
            Version = config_settings.get("Debug Function", "Version")
            if Version not in compatible_conf_version:
                logger.error('Incompatible profiles：' + Version + ", Require：" + "/".join(compatible_conf_version))
                print("Incompatible configuration files, please delete and try again.")
                if WINOS: print('Press any key to exit the program...'); os.system('pause>nul')
                os._exit(1)
            repository_url = config_settings.get("Download Settings", "Repository_Url")
            host_url = config_settings.get("Media Server", "Host_Url")
            api_key = config_settings.get("Media Server", "Host_API")
            max_download_connect = config_settings.getint("Download Settings", "MAX_DL")
            max_retries = config_settings.getint("Download Settings", "MAX_Retry")
            Proxy = config_settings.get("Download Settings", "Proxy")
            download_path = config_settings.get("Download Settings", "Download_Path")
            Conflict_Proc = config_settings.getint("Download Settings", "Conflict_Proc")
            max_upload_connect = config_settings.getint("Import Settings", "MAX_UL")
            Get_Intro = config_settings.getint("Import Settings", "Get_Intro")
            local_path = config_settings.get("Import Settings", "Local_Path")
            BD_App_ID = config_settings.get("Import Settings", "BD_App_ID")
            BD_API_Key = config_settings.get("Import Settings", "BD_API_Key")
            BD_Secret_Key = config_settings.get("Import Settings", "BD_Secret_Key")
            BD_VIP = config_settings.get("Import Settings", "BD_VIP")
            overwrite = config_settings.getint("Import Settings", "OverWrite")
            aifix = True if config_settings.get("Download Settings", "AI_Fix") == 'Yes' else False
            debug = True if config_settings.get("Debug Function", "DeBug") == 'Yes' or debugflag else False
            deleteall = True if config_settings.get("Debug Function", "DEL_ALL") == 'Yes' else False
            fixsize = config_settings.getint("Import Settings", "Size_Fix")
            # Fix the user'sURL
            if not host_url.endswith('/'): host_url += '/'
            if not repository_url.endswith('/'): repository_url += '/'
            # Create Folder
            if not os.path.exists('./Getter/'):
                os.makedirs('./Getter/')
            if not os.path.exists(download_path):
                os.makedirs(download_path)
            if not os.path.exists(local_path):
                os.makedirs(local_path)
                write_txt(local_path + "/README.txt",
                          'This directory is automatically generated so that you can store your own collected avatars (only JPG format is supported), which will be imported to the server as a priority. \n\nPlease backup your own copy of collected avatars, depending on your configuration, the directory file may be modified by the program.')
            # Define BaiduAI
            if fixsize == 3:
                BD_AI_client = AipBodyAnalysis(BD_App_ID, BD_API_Key, BD_Secret_Key)
            else:
                BD_AI_client = None
            logger.info('Configuration file read successfully')
            return (
                repository_url, host_url, api_key, overwrite, fixsize, max_retries, Proxy, aifix, debug,
                deleteall, download_path, local_path, max_download_connect, max_upload_connect, BD_AI_client, BD_VIP,
                Get_Intro, Conflict_Proc)
        except:
            logger.error('Configuration file read failure：' + format_exc())
            print('× Unreadable config.ini. If this is an old version of the configuration file, please delete it and try again.\n')
            if WINOS: print('Press any key to exit the program...'); os.system('pause>nul')
            sys.exit()
    else:
        content = '''### Gfriends Inputer configuration file ###

[Media Server]
### Emby / Jellyfin server address ###
Host_Url = 
	
### Emby / Jellyfin API key ###
Host_API = 

[Download Settings]
### Download folder ###
Download_Path = ./Downloads/

### Number of download threads ###
### If your network is unstable, has high packet loss or latency, reduce the number of download threads
### Too many requests
MAX_DL = 5

### Number of failed download retries ###
### Increase the number of failed retries if your network is unstable, has high packet loss, or has high latency
MAX_Retry = 3

### Girlfriend avatar repository source ###
### The "default" repository is the official main repository (browser access is disabled): https://raw.githubusercontent.com/gfriends/gfriends/master/
### Get more official alternate mirrors, see the project home page for details
Repository_Url = default

### AI optimization (only official repositories are supported) ###
### Automatically pick AI algorithm-optimized copies when downloading low-quality avatars is unavoidable, which are higher quality but take up more space.
AI_Fix = Yes

### Multiple avatar download method ###
### Multiple avatars of one girlfriend may be stored in the repository, in most cases the best one will be selected automatically.
### You can also let the program download all the corresponding avatars and remind you to pick them manually before importing them.
# This option is not available when running in "Silent Mode" background; not recommended to share with "Incremental Update" feature
# 0 - Automatic preference
# 1 - Manual selection (choose carefully, especially if you have a large number of avatars to import)
Conflict_Proc = 0

### HTTP / Socks local proxy ###
### It is recommended to enable global proxy instead of using this local proxy
### HTTP proxy format is http://IP:端口 , e.g. http://localhost:7890
# Socks proxy format is socks+protocol version://IP:port , e.g. socks5h://localhost:7890
Proxy = 

[Import Settings]
### Search for girlfriend's personal information ###
### Scrape the actor information and import it, using the actor's original Japanese name works best.
# # # To reduce the load on the source site, only single-threaded for now, so it will slow down the import speed.
# 0 - No personal information search
# 1 - Get personal information from XSlist
Get_Intro = 1

### Local avatar folder ###
### Move third-party avatar packs or your own collected avatars to this directory, which can take precedence over repository imports to the server. Only jpg format is supported.
Local_Path = ./Avatar/

### Avatar import method (only official repositories are supported) ###
### 0 - No overwrite
### 1 - Overwrite all
### 2 - Incremental import (overwrite when avatars are updated)
OverWrite = 2

### Number of threads imported ###
### When importing to a local or intranet server, the number of threads can be increased if the network is stable (recommended: 20-100)
# This option is not available when "Search for personal information" is turned on
MAX_UL = 20

### Avatar size optimization ###
### Avoid media server stretching avatars that do not match 2:3 ratio
# 0 - Import without processing
# 1 - Gaussian smoothing (filled with hairy glass style)
# 2 - Direct crop processing (may crop to actor's face)
# 3 - Local AI detection and cropping (default, speed depends on device performance)
# 4 - Cloud AI detection and cropping (requires configuration of Baidu Body Positioning AI)
Size_Fix = 3

### Baidu Body Positioning AI ### Enable using Yes - No
# See the repository project README for specific instructions
# Free personal users QPS=2 Slow processing speed. Paid personal users and enterprise users please modify BD_VIP for your purchased QPS quota value, free personal users will report an error after modification.
BD_VIP = No
BD_App_ID = 
BD_API_Key = 
BD_Secret_Key = 

[Debug Function]
### Delete all actor avatars and actor metadata ### Enable using Yes - No
### Support deleted avatars: Primary / Thumb / Backdrop (usually imported by MDCx)
### ### Metadata supported for deletion: ProviderIds / Taglines / Genres / Tags / Overview, items with locked metadata will not be deleted.
# Note: The delete operation is not reversible!
DEL_ALL = No

### DEBUG debug mode ### Enable using Yes - No
### DEBUG mode is equivalent to starting the program with the --debug parameter, which slows down the program when turned on.
### Please check and upload the DEBUG log file before committing the issue.
DeBug = Yes

### Configuration file version ###
Version = '''
        write_txt("config.ini", content + version)
        logger.warning('Configuration file not found, regenerated')
        print('× Not found config.ini.It has been generated for you, please modify the configuration and re-run the program.\n')
        if WINOS: print('Press any key to exit the program...');    os.system('pause>nul')
        sys.exit()


def read_persons(host_url, api_key):
    rewriteable_word('>> Connections Emby / Jellyfin Server...')
    host_url_persons = host_url + 'Persons?api_key=' + api_key  # &PersonTypes=Actor
    try:
        rqs_emby = session.get(url=host_url_persons, proxies=host_proxies, timeout=60, verify=False)
    except requests.exceptions.ConnectionError:
        logger.error('Connections Emby / Jellyfin Server failure:' + host_url_persons + format_exc())
        print('× Connections Emby / Jellyfin Server failed, please check if the address is correct:', host_url_persons, '\n')
        sys.exit()
    except requests.exceptions.RequestException:
        logger.error('Connections Emby / Jellyfin server timeout: ' + host_url_persons + format_exc())
        print('× Connections Emby / Jellyfin server timed out, please check if the address is correct:', host_url_persons, '\n')
        sys.exit()
    except:
        logger.error('Connections Emby / Jellyfin server unknown error: ' + host_url_persons + format_exc())
        print('× Connections Emby / Jellyfin server unknown error:', host_url_persons, '\n')
        sys.exit()
    if rqs_emby.status_code == 401:
        logger.error('Emby / Jellyfin Back: 401 API not authorized')
        print('× No access rights Emby / Jellyfin server, please check if the API key is correct \n')
        sys.exit()
    elif rqs_emby.status_code == 404:
        logger.error('Emby / Jellyfin Back 404 API not found and alternative API is also invalid')
        print('× Try to read Emby / Jellyfin actors list but not found, probably unadapted version:', host_url_persons, '\n')
        sys.exit()
    elif rqs_emby.status_code != 200:
        logger.error('Emby / Jellyfin Back :' + str(rqs_emby.status_code))
        print('× Connections Emby / Jellyfin server successful, but server internal error: ' + str(rqs_emby.status_code))
        sys.exit()
    # If 'json' is not in rqs_emby.headers['Content-Type']: # Gunfai return type is text/html?
    # print('× Connections Emby / Jellyfin server succeeded, but the server's actor list is not recognized:' + rqs_emby.headers['Content-Type'] )
    # sys.exit()
    try:
        output = sorted(loads(rqs_emby.text)['Items'], key=lambda x: x['Name']) # sort by name
        logger.info('Connections Emby / Jellyfin server successful, contains actors: ' + str(len(output)))
        print('√ Connections Emby / Jellyfin server successful')
        print(' Performers: ' + str(len(output)) + ' people \n')
        return output
    except:
        logger.error('Emby / Jellyfin The response cannot be resolved as Json:' + rqs_emby.headers['Content-Type'] )
        print('× Connections Emby / Jellyfin server succeeded, but the server actor list is not recognized:' + rqs_emby.headers['Content-Type'])
        sys.exit()


def write_txt(filename, content):
    txt = open(filename, 'a', encoding="utf-8")
    txt.write(content)
    txt.close()


def rewriteable_word(word):
    for t in ['', word]: sys.stdout.write('\033[K' + t + '\r')


def del_all():
    print('【Debugging mode】Delete all avatars and messages\n')
    list_persons = read_persons(host_url, api_key)
    rewriteable_word('Press any key to start...')
    os.system('pause>nul') if WINOS else input('Press Enter to start...')
    with alive_bar(len(list_persons), enrich_print=False, dual_line=True) as bar:
        for dic_each_actor in list_persons:
            bar.text('Being deleted：' + dic_each_actor['Name'])
            bar()
            del_avatar(dic_each_actor['Id'], dic_each_actor['Name'])
            while True:
                if not threading.active_count() > max_upload_connect + 1: break
    rewriteable_word('>> Nearing completion')
    for thr_status in threading.enumerate():
        try:
            thr_status.join()
        except RuntimeError:
            continue
    print('√ Delete completed  ')
    if WINOS: print('Press any key to exit the program...'); os.system('pause>nul')
    sys.exit()


@asyncc
def get_ip():
    global public_ip
    try:
        response = session.get('https://api.myip.la/cn?json')
        ip_country_code = loads(response.text)['location']['country_code']
        ip_country_name = loads(response.text)['location']['country_name']
        ip_city = loads(response.text)['location']['province']
        if ip_country_name == ip_city:
            public_ip = '[' + ip_country_code + ']' + ip_country_name
        else:
            public_ip = '[' + ip_country_code + ']' + ip_country_name + ip_city
    except:
        pass


def check_update():
    rewriteable_word('>> Check for updates...')
    try:
        get_ip()
        response = session.get('https://api.github.com/repos/gfriends/gfriends-inputer/releases', timeout=5)
        response.encoding = 'utf-8'
        """
        if response.status_code != 200:
            print('× Check for update failure！An error was returned：' + str(response.status_code))
            logger.warning('Check for update failure！An error was returned：' + str(response.status_code))
            rewriteable_word('Press any key to skip...')
            os.system('pause>nul') if WINOS else input('Press Enter to skip...')
        """
        # version process
        # `v2.94` > `2.94`
        # `v3.0.0` > `3.0.0` > `0.0.3` > `00.3` > `3.00`
        local_ver = version.replace('v', '')
        remote_ver = loads(response.text)[0]['tag_name'].replace('v', '')
        if remote_ver.count('.') > 1:
            remote_ver = remote_ver[::-1].replace('.', '', 1)[::-1]
        if local_ver.count('.') > 1:
            local_ver = local_ver[::-1].replace('.', '', 1)[::-1]

        if (float(local_ver) < float(remote_ver)) and not quiet_flag:
            logger.info('New Version Detected：' + str(local_ver) + ' -> ' + str(remote_ver))
            print(loads(response.text)[0]['name'] + ' Posted！\n')
            print(loads(response.text)[0]['body'])
            print('Learn more：https://git.io/JL0tk\n')

            # Get the new version download link
            download_link = ""
            for item in loads(response.text)[0]['assets']:
                if sys.platform.startswith('win') and (
                        'windows' in item['browser_download_url'] or 'Windows' in item['browser_download_url']):
                    download_link = item['browser_download_url']
                    break
                if sys.platform.startswith('darwin') and (
                        'macos' in item['browser_download_url'] or 'macOS' in item['browser_download_url']):
                    download_link = item['browser_download_url']
                    break
                if sys.platform.startswith('linux') and (
                        'ubuntu' in item['browser_download_url'] or 'Linux' in item['browser_download_url']):
                    download_link = item['browser_download_url']
                    break

            # Download the new version
            if download_link:
                response = requests.get(download_link, stream=True)  # Must be streamed
                got_size = 0  # Initialize Downloaded Size
                chunk_size = 1024  # Size of data per download
                content_size = int(response.headers['content-length'])  # Total Download File Size
                try:
                    if response.status_code == 200:  # Determine if the response is successful
                        response.iter_content(chunk_size=chunk_size)
                        with alive_bar(content_size, enrich_print=False, dual_line=True, monitor='{percent:.0%}',
                                       elapsed=False,
                                       stats=False, spinner=None, receipt=True) as bar:
                            with open("./update.zip", 'wb') as file:  # Show progress bar
                                for data in response.iter_content(chunk_size=chunk_size):
                                    file.write(data)
                                    got_size += len(data)
                                    bar(len(data))
                                    bar.text(
                                        'Download in：%.2fMB/%.2fMB' % (
                                            float(got_size / 1024 / 1024), float(content_size / 1024 / 1024)))

                        print("update.zip Downloaded successfully, Please unzip and use the new version.")
                        logger.info("Update package downloaded successfully")
                    else:
                        print("Download failed, Please download through the details link above. Server return：", response.status_code)
                        logger.warning("Update package download failed, Server return：", response.status_code)
                except:
                    print("Update package download failed, Please download manually：", download_link)
                    logger.warning("Update package download failed：", format_exc())

            print("")
            rewriteable_word('Press any key to exit...')
            os.system('pause>nul') if WINOS else input('Press Enter to exit...')
            os._exit(0)
        else:
            logger.info('No new version detected')
    except requests.exceptions:
        logger.warning('Network problem causes update check failure, Skip updates' + format_exc())
        print('× Check for update failure, Unstable network connection！\n')
        print('Skipping updates soon.')
        time.sleep(3)
    except:
        logger.warning('Update check failed, Skip updates：' + format_exc())
        print('× Check for update failure！\n')
        print('About to skip the update.')
        time.sleep(3)
    if WINOS and not quiet_flag:
        # Clear Screen
        os.system('cls')


# Logger
if not os.path.exists('./Getter/'): os.makedirs('./Getter/')
if os.path.exists('./Getter/logger.log'): os.remove('./Getter/logger.log')
logger = logging.getLogger()
logging.basicConfig(filename='./Getter/logger.log',
                    format='%(asctime)s - [%(levelname)s]%(lineno)d:%(funcName)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S", encoding="utf-8", level=logging.INFO)

WINOS = True if sys.platform.startswith('win') else False
if WINOS:
    os.system('title Gfriends Inputer ' + version)
else:
    # The default working directory for Unix-like systems is not in the folder where the program is located
    config_path = '/'.join((sys.argv[0].replace('\\', '/')).split('/')[:-1])
    work_path = os.getcwd().replace('\\', '/')
    if work_path != config_path:
        os.chdir(config_path)  # Switching the working directory
    logger.debug('Fixing the running directory：' + config_path + ':' + work_path)

(config_file, quiet_flag, update_flag, debugflag) = argparse_function(version)
# if quiet_flag:
#   sys.stdout = open("./Getter/quiet.log", "w", buffering=1)
(repository_url, host_url, api_key, overwrite, fixsize, max_retries, Proxy, aifix, debug, deleteall,
 download_path, local_path, max_download_connect, max_upload_connect, BD_AI_client, BD_VIP, Get_Intro,
 Conflict_Proc) = read_config(config_file)
del debugflag, config_file

# Modify logger properties according to configuration
logger = logging.getLogger()
if debug:
    logger.setLevel(logging.DEBUG)
elif quiet_flag:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.INFO)

# Initialize the log and then try to introduceCV2
if fixsize == 3:
    from Lib.cv2dnn import find_faces

# Local Proxy
if Proxy:
    proxies = host_proxies = {'http': Proxy, 'https': Proxy}
    # Determine the intranet server based on IP
    if re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", host_url):
        ip = reduce(lambda x, y: (x << 8) + y,
                    map(int, re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", host_url)[0].split('.')))
        net_a = reduce(lambda x, y: (x << 8) + y, map(int, '10.255.255.255'.split('.'))) >> 24
        net_b = reduce(lambda x, y: (x << 8) + y, map(int, '172.31.255.255'.split('.'))) >> 20
        net_c = reduce(lambda x, y: (x << 8) + y, map(int, '192.168.255.255'.split('.'))) >> 16
        if ip >> 24 == net_a or ip >> 20 == net_b or ip >> 16 == net_c:
            host_proxies = {'http': None, 'https': None}
        del net_a, net_b, net_c, ip
    elif 'localhost' in host_url:
        host_proxies = {'http': None, 'https': None}
else:
    proxies = host_proxies = None

# Persistent Sessions
session = requests.Session()
session.mount('http://', requests.adapters.HTTPAdapter(max_retries=max_retries, pool_connections=100, pool_maxsize=100))
session.mount('https://',
              requests.adapters.HTTPAdapter(max_retries=max_retries, pool_connections=100, pool_maxsize=100))
session.headers = {"User-Agent": 'Gfriends_Inputer/' + version.replace('v', '')}
session.proxies = proxies

# Check for updates
public_ip = None
if update_flag and not quiet_flag: check_update()
if deleteall: del_all()

# Variable initialization
num_suc = num_fail = num_skip = num_exist = 0
exist_list = []
pic_path_dict = {}
actor_dict = {}
link_dict = {}
inputed_dict = {}
proc_flag = False
if Get_Intro:
    max_upload_connect /= 5

print('Gfriends Inputer ' + version)
print('https://git.io/gfriends\n')
logger.info('Gfriends Inputer ' + version + ' Successful start-up')

if not quiet_flag:
    rewriteable_word('Press any key to start...')
    os.system('pause>nul') if WINOS else input('Press Enter to start...')

# Proxy configuration tips
logger.info('Proxy Configuration：' + str(proxies) + ', IPAttribution：' + str(public_ip))
if not proxies:
    if public_ip and 'CN' in public_ip:
        print(public_ip, 'Recommend to enable global proxy\n')
    elif public_ip and 'CN' not in public_ip:
        print(public_ip, 'Non-mainland China visits\n')
    else:
        print('Recommend to enable global proxy\n')
else:
    if public_ip and 'CN' in public_ip:
        print(public_ip, 'Connected Local Agent, But this proxy does not seem to have the efficacy of scientific acceleration\n')
    elif public_ip and 'CN' not in public_ip:
        print(public_ip, 'Connected Local Agent\n')
    else:
        print('Local proxy configured ' + Proxy + ', But it does not seem to connect, please check its format and availability\n')

try:
    list_persons = read_persons(host_url, api_key)
    # list_persons = [{'Name': '@YOU', 'ServerId': 'be208b8f79ed449aacf99a1a23530488', 'Id': '59932', 'Type': 'Person', 'ImageTags': {'Primary': '3ad658cbfb0173e14bb09d255e84d64a'}, 'BackdropImageTags': []}]
    gfriends_map = get_gfriends_map(repository_url)
    actor_log = open('./Getter/Cast List.txt', 'w', encoding="UTF-8", buffering=1)
    actor_log.write(
        '【Cast List】\nThe list is for reference only, there may be other peoples names such as directors, writers, sponsors, etc. below, but the girlfriend avatar warehouse will only include Japanese girlfriends. \n Has matched to the avatar will be based on personal configuration, download and import or will be skipped\n\n')

    logger.info('Engine initialization')
    rewriteable_word('>> Engine initialization...')
    md5_persons = md5(str(list_persons).encode('UTF-8')).hexdigest()[14:-14]
    md5_config = md5(open('config.ini', 'rb').read()).hexdigest()[14:-14]  # md5Calculation supports only byte streams
    if os.path.exists('./Getter/proc.tmp'):  # Interruption records available, Then read the records line by line
        with open('./Getter/proc.tmp', 'r', encoding='UTF-8') as file:
            proc_list = file.read().split('\n')
        if md5_persons in proc_list and md5_config in proc_list:  # After the last interruption, No changes to the cast list and profile before trying to renew the upload
            proc_flag = True
    proc_log = open('./Getter/proc.tmp', 'w', encoding="UTF-8", buffering=1)
    proc_log.write('## Gfriends Inputer Breakpoint logging ##\n' + md5_persons + '\n' + md5_config + '\n')

    for dic_each_actor in list_persons:
        actor_name = dic_each_actor['Name']
        actor_id = dic_each_actor['Id']
        if dic_each_actor['ImageTags']:
            num_exist += 1
            exist_list.append(actor_name)
            if not overwrite:
                actor_log.write('Skip：' + actor_name + '\n')
                num_skip += 1
                continue
        if not os.path.exists(local_path + actor_name + ".jpg"):
            pic_link = get_gfriends_link(actor_name)
            if not pic_link:
                old_actor_name = actor_name
                actor_name = re.sub(r'（.*）', '', actor_name)
                actor_name = re.sub(r'\(.*\)', '', actor_name)
                pic_link = get_gfriends_link(actor_name)
                if not pic_link:
                    actor_log.write('Not found：' + actor_name + '\n')
                    num_fail += 1
                    continue
                if old_actor_name in exist_list:
                    exist_list.remove(old_actor_name)
                    exist_list.append(actor_name)
            actor_log.write('Download：' + actor_name + '\n')
            link_dict[actor_name] = pic_link
        actor_dict[actor_name] = actor_id
    actor_log.close()

    # Incremental update logic
    if overwrite == 2 and not Conflict_Proc:
        md5_host_url = md5(host_url.encode('UTF-8')).hexdigest()[14:-14]
        if os.path.exists('./Getter/down' + md5_host_url + '.log'):  # There are download records, Then read the records line by line
            with open('./Getter/down' + md5_host_url + '.log', 'r', encoding='UTF-8') as file:
                downlog_list = file.read().split('\n')
            down_log = open('./Getter/down' + md5_host_url + '.log', 'w', encoding="UTF-8")
            if md5_config in downlog_list:
                for item in downlog_list:
                    if '|' in item:
                        inputed_dict[item.split('|')[0]] = item.split('|')[1]
                    elif item == '':
                        pass
                    down_log.write(item + '\n')
            else:
                down_log.write(
                    '## Gfriends Inputer Importing records ##\n## Please note: Deleting this file will cause the server to ' + host_url + ' The incremental update function resets the\n' + md5_config + '\n')
            down_log.close()

        for index, actor_name in enumerate(list(link_dict)):  # There are operations to delete dictionaries, Cannot traverse the dictionary directly
            try:
                # if WINOS and not quiet_flag and index % 5 == 0:
                #    rewriteable_word('>> Engine initialization... ' + str(index) + '/' + str(len(list(link_dict))))
                proc_md5 = md5((actor_name + '+0').encode('UTF-8')).hexdigest()[13:-13]
                if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                    check_avatar(link_dict[actor_name], actor_name, proc_md5)  # Record the completed operation of the check into the subthread, In case the breakpoint is not recorded before the end of the download
                else:
                    proc_log.write(proc_md5 + '\n')
            except KeyboardInterrupt:
                sys.exit()
            except:
                logger.warning('Skip Check：' + str(actor_name) + format_exc())
                print('× Skip Check：' + str(actor_name) + '\n')
                continue
    if proc_flag:
        print('√ Engine initialization successful, Try to continue from the last interrupted position')
        logger.info('Engine initialization successful, Breakpoint transfer mode')
    else:
        print('√ Engine initialization successful                      ')
        logger.info('Engine initialization successful')

    if not link_dict:
        print('\n√ No avatar to download')
        logger.info('No avatar to download')
    else:
        print('\n>> Download avatar...')
        logger.info('Start downloading avatars')
        with alive_bar(len(link_dict), enrich_print=False, dual_line=True) as bar:
            for actor_name, link in link_dict.items():
                try:
                    if Conflict_Proc == 1 and not quiet_flag:
                        bar.text('Downloading now：' + re.sub(r'（.*）', '', actor_name) + ' [' + str(
                            len(link)) + ' Piece]') if '（' in actor_name else bar.text(
                            'Downloading now：' + actor_name + ' [' + str(len(link)) + ' Piece]')
                    else:
                        bar.text('Downloading now：' + re.sub(r'（.*）', '', actor_name)) if '（' in actor_name else bar.text(
                            'Downloading now：' + actor_name)
                    bar()
                    proc_md5 = md5((actor_name + '+1').encode('UTF-8')).hexdigest()[13:-13]
                    if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                        download_avatar(link, actor_name, proc_md5)  # Record the completed download operation into a sub-thread, In case the breakpoint is not recorded before the end of the download
                    else:
                        proc_log.write(proc_md5 + '\n')
                    while True:
                        if threading.active_count() > max_download_connect + 1:
                            time.sleep(0.01)
                        else:
                            break
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    with bar.pause():
                        logger.warning('Network connection exception, download failed：' + str(actor_name) + format_exc())
                        print('× Network connection exception and retry ' + str(max_retries) + ' failure')
                        print('× Please try to enable global proxy or configure local proxy；If proxy is enabled, Please check its availability')
                        print('× Press any key to continue running to skip downloading these avatars：' + str(actor_name) + '\n')
                        os.system('pause>nul') if WINOS else input()
                    continue
        rewriteable_word('>> Nearing completion')
        for thr_status in threading.enumerate():  # Waiting for the subthread to finish running
            try:
                thr_status.join()
            except RuntimeError:
                continue
        print('√ Download completed  ')
        logger.info('Avatar download completed')

    if Conflict_Proc == 1 and not quiet_flag:
        logger.info('Suspension of operation, requesting the user to manually pick an avatar')
        print('\nYou have enabled multiple avatars in the profile of "Manual Pick"')
        print('Please check the download directory, remove avatars you do not like')
        print('\n1. It is best to keep only one avatar for each girlfriend, otherwise the program will automatically choose a better one')
        print('2. If all the avatars of a certain girlfriend are deleted, it means that the avatars of that girlfriend will not be imported (does not affect the local import function)\n')
        rewriteable_word('After completing the selection, press any key to continue...')
        os.system('pause>nul') if WINOS else input('Press Enter to continue...')
        logger.info('The program continues to run')
        # Build path mapping
        files = os.listdir(download_path)
        files.sort()
        temp_list = []
        for filename in reversed(files):
            actorname = filename.replace('.jpg', '')
            actorname = re.sub(r'-\d+', '', actorname)
            if '.jpg' in filename and actorname in actor_dict and actorname not in temp_list:
                pic_path_dict[filename] = os.path.join(download_path, filename)
                temp_list.append(actorname)
            else:
                # Delete redundant avatars
                os.remove(os.path.join(download_path, filename))
        del temp_list
    else:
        # Build path mapping
        for filename in os.listdir(download_path):
            actorname = filename.replace('.jpg', '')
            if '.jpg' in filename and actorname in actor_dict:
                if overwrite == 2:
                    if actorname in link_dict:  # link_dict has been initialized and filtered, key is the name of the actor to be imported
                        pic_path_dict[filename] = download_path + filename
                else:
                    pic_path_dict[filename] = download_path + filename
    logger.info('Download avatar directory build complete')
    for root, dirs, files in os.walk(local_path):
        for filename in files:
            actorname = filename.replace('.jpg', '')
            file_path = os.path.join(root, filename)
            if '.jpg' in filename and actorname in actor_dict:
                if overwrite == 2 and actorname in exist_list:  # Overwrite import and now the avatar does not exist
                    actor_md5 = md5(actorname.encode('UTF-8')).hexdigest()[12:-12]
                    file_size = str(os.path.getsize(file_path))
                    if actor_md5 not in inputed_dict or inputed_dict[actor_md5] != file_size:
                        pic_path_dict[filename] = file_path
                    inputed_dict[actor_md5] = file_size
                else:
                    pic_path_dict[filename] = file_path
    logger.info('Local avatar directory build completed')

    if pic_path_dict:
        if fixsize:
            print('\n>> Size optimization...')
            logger.info('Start optimizing avatar size')
            with alive_bar(len(pic_path_dict), enrich_print=False, dual_line=True) as bar:
                for filename, pic_path in pic_path_dict.items():
                    bar.text(
                        'Being optimized：' + re.sub(r'（.*）', '', filename).replace('.jpg',
                                                                            '')) if '（' in filename else bar.text(
                        'Being optimized：' +
                        filename.replace('.jpg', ''))
                    bar()
                    proc_md5 = md5((filename + '+2').encode('UTF-8')).hexdigest()[13:-13]
                    if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                        result = fix_size(fixsize, pic_path)
                        if not result: pic_path_dict.pop(filename)
                    proc_log.write(proc_md5 + '\n')
            print('√ Optimization completed  ')
            logger.info('Size optimization completed')
        else:
            logger.info('Unopened avatar size optimization')

        print('\n>> Importing avatars...')
        logger.info('Importing avatars')
        with alive_bar(len(pic_path_dict), enrich_print=False, dual_line=True) as bar:
            for filename, pic_path in pic_path_dict.items():
                actorname = filename.replace('.jpg', '')
                actorname = re.sub(r'1-\d+', '', actorname)
                bar.text(
                    'Being imported：' + re.sub(r'（.*）', '', filename).replace('.jpg', '')) if '（' in filename else bar.text(
                    'Being imported：' + actorname)
                bar()
                proc_md5 = md5((filename + '+3').encode('UTF-8')).hexdigest()[13:-13]
                if not proc_flag or (proc_flag and not proc_md5 in proc_list):
                    with open(pic_path, 'rb') as pic_bit:
                        b6_pic = b64encode(pic_bit.read())
                    url_post_img = host_url + 'Items/' + actor_dict[actorname] + '/Images/Primary?api_key=' + api_key
                    input_avatar(url_post_img, b6_pic)
                    if Get_Intro == 1:
                        bar.text(
                            'Search Information：' + re.sub(r'（.*）', '', filename).replace('.jpg',
                                                                                '')) if '（' in filename else bar.text(
                            'Search Information：' + actorname)
                        xslist_search(actor_dict[actorname], actorname)
                proc_log.write(proc_md5 + '\n')
                while True:
                    if threading.active_count() > max_upload_connect + 1:
                        time.sleep(0.01)
                    else:
                        break
                num_suc += 1
        rewriteable_word('>> Nearing completion')
        for thr_status in threading.enumerate():  # Waiting for the subthread to finish running
            try:
                thr_status.join()
            except RuntimeError:
                continue
        print('√ Import completed  ')
        print(
            '\nEmby / Jellyfin Performers in total ' + str(len(list_persons)) + ' persons, of which ' + str(num_exist) + ' people with existed avatars')
        print('This import/ update ' + str(num_suc) + ' avatars, and ' + str(num_fail) + ' people without avatars\n')
        logger.info(
            'Importing avatars is complete, Success / Failure / Presence / Total：' + str(num_suc) + '/' + str(num_fail) + '/' + str(num_exist) + '/' + str(
                len(list_persons)))
        if not overwrite:
            print('-- Unopened to override existing avatars, so some actors were skipped, see the list of records in the Getter directory for details')
    proc_log.close()
    os.remove('./Getter/proc.tmp')
    if overwrite == 2 and not Conflict_Proc:
        down_log = open('./Getter/down' + md5_host_url + '.log', 'w', encoding="UTF-8")
        down_log.write(
            '## Gfriends Inputer Importing records ##\n## Please note: deleting this file will cause the incremental update function of the server ' + host_url + ' to be reset\n' + md5_config + '\n')
        for key, value in inputed_dict.items():
            down_log.write(key + '|' + value + '\n')
        down_log.close()
    else:
        print('\n√ There are no avatars to import')
        logger.info('There are no avatars to import')
except KeyboardInterrupt:
    logger.info('User forced stop')
    print('× User forced stop')
except SystemExit:
    logger.error('Known errors')
    print('× Known errors, See the logger.log log file in the Getter directory.')
except:
    logger.error('Unknown error：' + format_exc())
    print('× Unknown error, See the logger.log log file in the Getter directory.')
if WINOS and not quiet_flag:
    print('Press any key to exit the program...')
    os.system('pause>nul')
logger.info('Exit Procedures')
