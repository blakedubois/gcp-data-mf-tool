## Overview

This is a command line tool for working with artifacts manifest.
Main purpose is to generate and update **manifest.json** file that contains all information
about last successful builds and assets, that build generates.

Overall manifest shows:
- last successful build for each branch in scopr of repository and all assets produces by a build

## Build


For cloud build step this util have to be a docker container. 
Just submit cloudbuild or build docker image manually.
```
$  gcloud builds submit --config=cloudbuild.yaml .
```

Or install in manually by
```
$  python3 setup.py install
```

## Configuration file

Configuration file contains static description of the project and produced artifacts for updating the manifest.


Structure of a project that we assume:
 - Project are represented by **semantic name**.
   It can be repository name (like GitHub repo, or any human readable name of the project)

- Project contains one or many **components**. It’s useful to take it as if the project
  contains several semantic parts (a.k.a. modules). For example:
  - Project **my-bigdata-app-1** contains 2 submodules (Luigi python scripts and spark app).
    Make sense to separate them on 2 components: **luigi-scripts** and **spark-app**
  - Project **my-maven-app** is a plain maven application. Well it produces only one artifact and make
    sense to use one component for it.

- Each component produces one or more assets or artifacts.


This structure is configured solely through the JSON .mf.json file stored (by default) in the root directory of your repository.

```json
{
  "bucket": "<artifacts bucket>",
  "repository": "<semantic name>",
  "components": {
    "<name of the component>": {
      "type": "<type of the component>",
      "assets": [
        {
          "glob": "<UNIX glob pattern>"
        }
      ]
    }
  }
}

```

- bucket (type: string) - name of GCS bucket used for storing artifacts and the manifest.json file
- repository (type: string) - semantic name of current repository
- components (type: object)
    - each key is a name of the component
    - each value is a component's config
- type (type: string) type of component, TBD
- assets (type: array) config for assets
  - glob (type: string) unix pattern, every found file by pattend will be uploaded separatly and added into manifest.json


> NOTE:
> - component's name have to match pattent `^[-a-zA-Z0-9_]*$`
> - branch name is (slugified)[https://github.com/un33k/python-slugify] to be URL safe.


## Manifest structure



```json

{
   "@spec": 1,
   "@ns": {
      "example-branch": {
         "@last_success": {
            "@built_at": "2011-08-08T04:00:00.000Z",
            "@rev": "579539ea2763c4be1aebf6133637bd53372ed9ec",
            "@include": {
               "MyComponentABCD": {
                  "@type": "sparkJob | hiveJob | etc.",
                  "@metadata": {},
                  "@binaries": [
                     {
                        "@sha": "777c3a7ed83e44198b0a624976ec99822eb6f4a44bf1513eafbc7c13997cd86c",
                        "@ref": "gs://builds-bucket/my-bigdata-repo/master/579539e/MyComponentABCD/app.jar"
                     }
                  ]
               }
            }
         },
         "develop": {},
         "feature/ABS-01": {}
      }
   }
}

```

## Usage

Tool provider next functionality

##### Uploading

It is possible to upload artifacts on GCS as a result of latest succesful build (supposed to be Cloud Build).

>  $BRACH_NAME, $COMMIT_SHA and $BUILD_ID are substitutions. See [https://cloud.google.com/cloud-build/docs/configuring-builds/substitute-variable-values]


```
mfutil builds put --git_branch $BRACH_NAME --git_commit $COMMIT_SHA --build_id $BUILD_ID
```

This command will try to find local .mf.json file to discover GCS bucket and repository name. 
After that it will find all configured assets and uplaod to GCS

##### Listing

It is possible to take a look latest successful build and its artifacts. Next scenarios are available:

Take a look ALL builds and binaries for interested repository (names provide for example only)
```
$ mfutil builds list --bucket my_bucket --repo myrepo
{"branch": "master", "app": "gcp-data", "built_at": "2019-12-12T12:51:35.541773+00:00", "commit": "432521", "url": "gs://my_bucket/myrepo/master/6dfb5720/gcp-data/manifest.py"}
{"branch": "dev", "app": "gcp-data", "built_at": "2019-12-12T12:58:35.541773+00:00", "commit": "432521", "url": "gs://my_bucket/myrepo/dev/6dfb5720/gcp-data/manifest.py"}

```

Take a latest build's binaries for interested repository and **specific brunch**
```
$ mfutil builds latest ls --bucket my_bucket --repo myrepo --brunch dev
{"branch": "dev", "app": "gcp-data", "built_at": "2019-12-12T12:58:35.541773+00:00", "commit": "432521", "url": "gs://my_bucket/myrepo/dev/6dfb5720/gcp-data/manifest.py"}
```

Take a look builds and binaries for interested repository and specific brunch and app, a.k.a. some module
```
$ mfutil builds list --bucket my_bucket --repo myrepo --brunch dev --app gcp-data
{"branch": "dev", "app": "gcp-data", "built_at": "2019-12-12T12:58:35.541773+00:00", "commit": "432521", "url": "gs://my_bucket/myrepo/dev/6dfb5720/gcp-data/manifest.py"}
```


##### Downloading

It is possible to fetch interested binaries from GCS.

Fetch all binaries by last successful build for **specific branch**.

```
$ mfutil builds get --bucket my_bucket --repo myrepo --brunch dev /path/to/store
```


Fetch all binaries by last successful build for specific branch and target app.

```
$ mfutil builds get --bucket my_bucket --repo myrepo --brunch dev --app gcp-data /path/to/store 
```


## Testing

Just run
```
python -m unittest discover -s tests -p '*_test.py'
```