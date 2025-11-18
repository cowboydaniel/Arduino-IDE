import os

from pythonforandroid.recipes.pyjnius import PyjniusRecipe as BasePyjniusRecipe


class PyjniusRecipe(BasePyjniusRecipe):
    # Use the latest pyjnius release to avoid Cython 3 incompatibilities
    version = "1.7.0"
    url = "https://github.com/kivy/pyjnius/archive/{version}.zip"
    patches = BasePyjniusRecipe.patches + ["cython3-long-alias.patch"]

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)

        utils_path = os.path.join(self.get_build_dir(arch), "jnius", "jnius_utils.pxi")
        if not os.path.exists(utils_path):
            return

        marker = "# Alias removed Python 2 long to int for Cython 3"
        with open(utils_path, "r", encoding="utf-8") as file:
            content = file.read()

        if "long = int" in content:
            return

        updated = content.replace(
            "cdef str_for_c(s):\n    return s.encode('utf-8')\n\n",
            "cdef str_for_c(s):\n    return s.encode('utf-8')\n\n"
            f"{marker}\ntry:\n    long\nexcept NameError:\n    long = int\n\n",
            1,
        )

        if updated == content:
            updated = f"{marker}\ntry:\n    long\nexcept NameError:\n    long = int\n\n" + content

        with open(utils_path, "w", encoding="utf-8") as file:
            file.write(updated)


recipe = PyjniusRecipe()
