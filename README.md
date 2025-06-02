# cabot-image-desc

This server API provides functions to describe surrounding of the user of the suitcase by utilizing GPT.

## environment variable

- edit .env file

```
OPENAI_API_KEY=<key>

# default lng=0, lat=0, rotate=0, zoom=21, please specify the center of your environment
INITIAL_LOCATION='{"lng": -79.94565, "lat": 40.44335, "rotate": 1, "zoom": 21}'

# set API_KEY for remote access
API_KEY=

# if you want to use web UI, set users and passwords
USERNAMES=<user1>[,<user2>]...
PASSWORDS=<pass1>[,<pass2>]...

# if you want to use remote MONGODB or use different db name, change them from default
MONGODB_HOST=mongodb://mongo:27017/
MONGODB_NAME=geo_image_db

# if you want to use ollama
LLM_AGENT=  # ollama or ollama-2step
OLLAMA_HOST=
AGENT_VLM=
AGENT_LLM=  # for ollama-2step
```

## Web UI

- `<host_name>`/index.html : plot image locations on a map, test image description
- `<host_name>`/list.html : list all images

## data

- `./images` is mounted into docker container (docker-container-upload.yaml)
- Put all images into `./images` dir
- Put the exported json file into `./images` dir

## build docker image

```
./bake-docker.sh -i
```

## run web app

- You need to upload images or import data to see data on the web app

```
./launch.sh
```

### development

```
./launch.sh -d   # launch server with dev env (reload code when changed)
./launch.sh -t   # launch pytest with dummy OpenAI APIs
./launch.sh -o   # launch pytest with actual OpenAI APIs
./launch.sh -l   # launch lint test
```

## manage images

- Use `manage-images.sh` to upload images, add tags, check EXIF data, and more.
- You can specify a local image or a local directory  (do not need to put them under ./images dir, but images dir will be mounted to docker container at this moment)

```
# Upload a single image or all images in a directory  (if there is already description in the db, do not nothing)
./manage-images.sh -i <image_file>
./manage-images.sh -I <directory>  

# Re-generate description
./manage-images.sh -i <image_file> -r
./manage-images.sh -I <directory> -r

# (Re-)generate description with a prompt (see default-prompt.txt)
./manage-images.sh -i <image_file> (-r) -p <prompt file>
./manage-images.sh -I <directory> (-r) -p <prompt file>

# Check EXIF data of the image/images
./manage-images.sh -i <image_file> -e
./manage-images.sh -I <directory>  -e

# Specify the floor of the image/images
./manage-images.sh -i <image_file> -F <floor> 
./manage-images.sh -I <directory>  -F <floor> 

# Add a tag / tags to the image/images
./manage-images.sh -i <image_file> -t <tag1> -t <tag2> 
./manage-images.sh -I <directory> -t <tag1> -t <tag2> 

# Rmove a tag / tags to the image/images
./manage-images.sh -i <image_file> -T <tag1> -T <tag2> 
./manage-images.sh -I <directory> -T <tag1> -T <tag2> 

# Clear all tags from the image/images
./manage-images.sh -i <image_file> -c
./manage-images.sh -I <directory> -c

# check json of the image
./manage-images.sh -i <image_file> -j

# List all json IDs
./manage-images.sh -l

# Remove the JSON ID from the database
./manage-images.sh -R <jsonid>
```

## import data

- Import json data
  - if there is existing data, update it

```
./manage-images.sh -P <json>
```

## export data

- Export json data

```
./manage-images.sh -X <json>
```
