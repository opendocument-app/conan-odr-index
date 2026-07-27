from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get
)


class OpenDocumentCoreConan(ConanFile):
    name = "odrcore"
    version = ""
    url = "https://github.com/opendocument-app/OpenDocument.core"
    homepage = "https://opendocument.app/"
    description = "C++ library that translates office documents to HTML"
    topics = "open document", "openoffice xml", "open document reader"
    license = "MPL-2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libmagic": [True, False],
        "with_http_server": [True, False],
        "with_cli": [True, False],
        "with_python": [True, False],
        "with_jni": [True, False],
        "bundle_assets": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libmagic": True,
        "with_http_server": True,
        "with_cli": True,
        "with_python": False,
        "with_jni": False,
        "bundle_assets": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.with_libmagic

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("pugixml/1.15")
        self.requires("cryptopp/8.9.0")
        self.requires("miniz/3.0.2")
        self.requires("nlohmann_json/3.12.0")
        self.requires("vincentlaucsb-csv-parser/2.3.0")
        self.requires("uchardet/0.0.8")
        self.requires("utfcpp/4.0.8")
        self.requires("argon2/20190702-odr")

        if self.options.with_http_server:
            self.requires("cpp-httplib/0.28.0")
        if self.options.get_safe("with_libmagic", False):
            self.requires("libmagic/5.45")
        if self.options.with_python:
            self.requires("pybind11/2.13.6")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def validate_build(self):
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 20)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["source"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_VERSION"] = self.version
        tc.variables["ODR_TEST"] = False
        tc.variables["ODR_WITH_LIBMAGIC"] = self.options.get_safe("with_libmagic", False)
        tc.variables["ODR_WITH_HTTP_SERVER"] = self.options.with_http_server
        # Consumers that only link the library (e.g. the mobile apps) can drop the
        # cli tools, which otherwise get built and installed with the package.
        tc.variables["ODR_CLI"] = self.options.with_cli
        tc.variables["ODR_PYTHON"] = self.options.with_python
        tc.variables["ODR_JNI"] = self.options.with_jni
        # Consumers that ship the libmagic database themselves and wire the path
        # at runtime (e.g. via odr::GlobalParams) can set this to False to skip
        # bundling it into the odrcore package at build time.
        tc.variables["ODR_BUNDLE_ASSETS"] = self.options.bundle_assets

        # When ODR_BUNDLE_ASSETS is on, odrcore's CMake copies the libmagic
        # database into its own data dir and needs its source path at configure
        # time. It never discovers it itself, so bridge it from the dependency's
        # runenv (exported by its package_info()); otherwise the build fails fast.
        runenv_info = Environment()
        for dep in self.dependencies.host.topological_sort.values():
            runenv_info.compose_env(dep.runenv_info)
        envvars = runenv_info.vars(self)
        tc.variables["LIBMAGIC_DATABASE_PATH"] = envvars.get("MAGIC")

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["odr"]
