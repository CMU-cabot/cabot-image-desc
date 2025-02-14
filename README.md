# cabot-image-desc

This server API provides functions to describe surrounding of the user of the suitcase by utilizing GPT.

## environment variable

- edit .env file

```
OPENAI_API_KEY=<key>

# default lng=0, lat=0, rotate=0, zoom=21, please specify the center of your environment
INITIAL_LOCATION='{"lng": -79.94565, "lat": 40.44335, "rotate": 1, "zoom": 21}'
```

## data

- `./images` is mounted into docker container (docker-container-upload.yaml)
- Put all images into `./images` dir
- Put the exported json file into `./images` dir

## build docker mage

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
./launch.sh -d
```

## upload image(s), add tag

- Uploaded image will be sent to OpenAI to get description and saved into local mongodb

```
./launch.sh -u ./image_uploader.py -f <image_file>
./launch.sh -u ./image_uploader.py -f <image_file> -r  # retry description
./launch.sh -u ./image_uploader.py -f <image_file> -t <tag1> -t <tag2> # clear and add tag
```

- Upload/update images in a dir
```
./launch.sh -u ./upload_all.sh -d <image_dir>   # dryrun to check which file will be uploaded
./launch.sh -u ./upload_all.sh <image_dir>
./launch.sh -u ./upload_all.sh -r <image_dir>   # retry description for all images
```

- Upload/update images in a dir with a tag
```
./launch.sh -u ./upload_all_with_tag.sh -d <image_dir> <tag>   # dryrun to check which file will be uploaded
./launch.sh -u ./upload_all_with_tag.sh <image_dir> <tag>      # clear and add tag to the images
```

## import data

- Import json data
  - if there is existing data, update it

```
./launch.sh -u ./import_data.py images/<import.json>
```

## export data

- Export json data
  - be careful, this script overwrite the file if exists

```
./launch.sh -u ./export_data.py images/<export.json>
```
