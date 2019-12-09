## Overview

This is a command line tool for working with artifacts manifest.
Main purpose is to generate and update **manifest.json** file that contains all information
about last successful builds and assets, that build generates.

Overall manifest shows:
- last successful build for each branch in scopr of repository and all assets produces by a build

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
                        "@ref": "gs://builds-bucket/my-bigdata-repo/master/579539e/spark/app.jar"
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

```
mfutil --git_sha $COMMIT_SHA \
       --git_branch $BRANCH_NAME \
       --build_id $BUILD_ID \
       --upload
```


## Build

```
gcloud builds submit \
--config=./cloudbuild.yaml .
```
