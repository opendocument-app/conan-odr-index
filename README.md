# conan-odr-index

A collection of packages necessary for https://github.com/opendocument-app/OpenDocument.core which is then used by our applications for Android https://github.com/opendocument-app/OpenDocument.droid and iOS https://github.com/opendocument-app/OpenDocument.ios.

The structure of this repository is similar to https://github.com/conan-io/conan-center-index but we rely on GitHub Actions for the build process and push the recipies and artifacts to our Artifactory instance https://artifactory.opendocument.app which is then used by the other builds.

Apart from GitHub Actions we have some custom Python scripts to support the enumeration of packages and versions. Since we do not always want to build all packages and all versions at the same time we have some selection mechanism. The configuration is steered by [`defaults.yaml`](./defaults.yaml).

Builds are triggered via a schedule and can be run manually for single packages and versions or for the default selection of packages. Builds of dependecies are managed only by conan which can result in duplicate builds.

- [Build all packages](https://github.com/opendocument-app/conan-odr-index/actions/workflows/build_all.yml)
- [Build one package](https://github.com/opendocument-app/conan-odr-index/actions/workflows/build_one.yml)
- [Clear packages](https://github.com/opendocument-app/conan-odr-index/actions/workflows/remove.yml)

Sometime our Artifactory is out of disk space. We have about 100 GB space but it gradually fills up and there seems no good way to auto clean it. This usually requires manual intervention on the machine but potentially the [Clear packages](https://github.com/opendocument-app/conan-odr-index/actions/workflows/remove.yml) workflow can help too.

## Limitations

- We cannot build different configurations of a package
  - Maybe this is not necessary and the client has to build the specific configuration if the default does not cover it
  - Potentially this can be modled via profiles, not sure if this is a good solution
