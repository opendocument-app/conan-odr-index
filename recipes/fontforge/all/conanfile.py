import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches, rmdir

required_conan_version = ">=2.0.6"

# @TODO: skip tests if private headers aren't installed,
# because current link test requires private headers


class FontForgeConan(ConanFile):
    name = "fontforge"
    package_type = "library"

    license = ("GPLv3-or-later", "revised-BSD")
    homepage = "https://fontforge.org"
    description = ("FontForge is a free (libre) font editor for Windows, Mac OS X and GNU+Linux. Use it to create, "
                   "edit and convert fonts in OpenType, TrueType, UFO, CID-keyed, Multiple Master, and many other "
                   "formats.")
    topics = "fonts"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "install_private_headers": [True, False],
        "with_tiff": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "install_private_headers": True,
        # @TODO: re-enable libtiff by default
        "with_tiff": False,
        # "with_tiff": True,
    }

    def requirements(self):
        self.requires("freetype/2.13.2")

        self.requires("libxml2/2.12.7")
        self.requires("giflib/5.2.2")
        self.requires("libjpeg/9f")
        self.requires("libpng/1.6.43")

        if self.options.with_tiff:
            self.requires("libtiff/4.6.0")

        # jbig and libdeflate are required by libtiff
        # Conan auto finds them, but linker doesn't, unless they're added here manually
        # self.requires("jbig/20160605")
        # self.requires("libdeflate/1.20")

        self.requires("glib/2.81.0-odr")

        if self.settings.os == "Android" and int(self.settings.os.get_safe("api_level")) < 23:
            self.requires("openlibm/0.8.3")

        if self.settings.os == "Android":
            self.requires("tmpfile/3.0.6")

    def build_requirements(self):
        self.tool_requires("gettext/0.22.5")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["ENABLE_GUI"] = "OFF"
        tc.variables["ENABLE_PYTHON_SCRIPTING"] = "OFF"
        tc.variables["ENABLE_PYTHON_EXTENSION"] = "OFF"
        tc.variables["ENABLE_LIBSPIRO"] = "OFF"
        tc.variables["ENABLE_LIBTIFF"] = self.options.with_tiff
        tc.variables["ENABLE_LIBREADLINE"] = "OFF"
        tc.variables["INSTALL_PRIVATE_HEADERS"] = self.options.install_private_headers
        tc.generate()

    def build(self):
        # Make sure msgfmt from build_tool gettext works properly (issue #16)
        self.run("which msgfmt")
        self.run("msgfmt --version")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # patch_folder = os.path.join(self.export_sources_folder, "patches/" + self.version)
        # if self.version == "20230101":
        #     patch(self, patch_file=os.path.join(patch_folder, "pie.patch"))
        # patch(self, patch_file=os.path.join(patch_folder, "FindGLib.patch"))


        # patch(self, patch_file=os.path.join(patch_folder, "InstallLibrary.patch"))


        # if (minSupportedSdk < 21) {
        #     // fontforge uses newlocale and localeconv, which are not available on Android pre 21 (Lollipop)
        #     // locale_t is available, we should not redefine it while using the BAD_LOCALE_HACK in splinefont.h
        #     //
        #     // From /usr/include/locale.h:
        #     // #if __ANDROID_API__ >= 21
        #     // locale_t duplocale(locale_t __l) __INTRODUCED_IN(21);
        #     // void freelocale(locale_t __l) __INTRODUCED_IN(21);
        #    // locale_t newlocale(int __category_mask, const char* __locale_name, locale_t __base) __INTRODUCED_IN(21);
        #     // #endif /* __ANDROID_API__ >= 21 */
        #     // ...
        #     // #if __ANDROID_API__ >= 21
        #     // struct lconv* localeconv(void) __INTRODUCED_IN(21);
        #     // #endif /* __ANDROID_API__ >= 21 */
        # patch(self, patch_file=os.path.join(patch_folder, "localeconv.patch"))
        # }

        # patch(self, patch_file=os.path.join(patch_folder, "handle-iconv-failure.patch"))

        # backport
        # patch(self, patch_file=os.path.join(patch_folder, "utf82def_copy_safe.patch"))

    def package(self):
        cmake = CMake(self)
        cmake.install()

        license_folder = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", self.source_folder, license_folder)
        copy(self, "COPYING.gplv3", self.source_folder, license_folder)

        for f in ["applications", "icons", "man", "metainfo", "mime"]:
            rmdir(self, os.path.join(self.package_folder, "share", f))

    def package_info(self):
        self.cpp_info.libs = ["fontforge"]
