import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
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
    license = "GPL 3.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_pdf2htmlEX": [True, False],
        "with_wvWare": [True, False],
        "with_libmagic": [True, False],
        "bundle_assets": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_pdf2htmlEX": True,
        "with_wvWare": True,
        "with_libmagic": True,
        "bundle_assets": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            # @TODO: ideally Windows should just default_options['with_pdf2htmlEX'] = False
            # But by the time config_options() is executed, default_options is already done parsed.
            del self.options.with_pdf2htmlEX
            del self.options.with_wvWare
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
        self.requires("cpp-httplib/0.28.0")

        if self.options.get_safe("with_pdf2htmlEX"):
            self.requires("pdf2htmlex/0.18.8.rc1-odr-git-732fd68")
        if self.options.get_safe("with_wvWare"):
            self.requires("wvware/1.2.9-odr")
        if self.options.get_safe("with_libmagic", False):
            self.requires("libmagic/5.45")

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
        tc.variables["WITH_PDF2HTMLEX"] = self.options.get_safe("with_pdf2htmlEX", False)
        tc.variables["WITH_WVWARE"] = self.options.get_safe("with_wvWare", False)
        tc.variables["WITH_LIBMAGIC"] = self.options.get_safe("with_libmagic", False)
        tc.variables["ODR_BUNDLE_ASSETS"] = self.options.get_safe("bundle_assets", True)

        # When ODR_BUNDLE_ASSETS is on, odrcore's CMake copies third-party data
        # files into its own data dir. Point it at each dependency's files
        # directly via the package folders (not via runenv) so bundling works.
        if self.options.get_safe("with_libmagic"):
            libmagic = self.dependencies["libmagic"].package_folder
            tc.variables["LIBMAGIC_DATABASE_PATH"] = os.path.join(libmagic, "res", "magic.mgc")
        if self.options.get_safe("with_pdf2htmlEX"):
            pdf2htmlex = self.dependencies["pdf2htmlex"].package_folder
            poppler_data = self.dependencies["poppler-data"].package_folder
            fontconfig = self.dependencies["fontconfig"].package_folder
            tc.variables["PDF2HTMLEX_DATA_PATH"] = os.path.join(pdf2htmlex, "share", "pdf2htmlEX")
            tc.variables["POPPLER_DATA_PATH"] = os.path.join(poppler_data, "share", "poppler")
            tc.variables["FONTCONFIG_DATA_PATH"] = os.path.join(fontconfig, "res", "share")

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
