import os.path

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        resdir = self.dependencies['poppler-data'].cpp_info.resdirs[0]
        for i in ["cMap", "cidToUnicode", "nameToUnicode", "unicodeMap"]:
            d = os.path.join(resdir, i)
            assert os.path.exists(d)
            assert len(os.listdir(d)) != 0
