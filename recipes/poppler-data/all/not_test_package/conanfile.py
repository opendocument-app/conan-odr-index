from conan import ConanFile
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        # self.cpp_info.resdirs = ["share/poppler"]
        # self.dependencies["poppler-data"].cpp_info.resdirs[0].replace("\\", "/")
        # print(self.cpp_info)
        from pprint import pprint
        # pprint(vars(self.cpp_info))
        # pprint(vars(self.cpp_info._package))
        # pprint(vars(self.cpp_info.components))
        pprint(self.cpp_info.components["ddd"]._resdirs)
        # for c in self.cpp_info.components:
        #     pprint(c.resdirs)
        # raise AssertionError(self.cpp_info.resdirs)
        # if not os.path.isdir(self.conf.get("user.poppler_mine-data:datadir", check_type=str)):
        #     raise AssertionError("datadir is not a directory")
