from pythonforandroid.recipes.pyjnius import PyjniusRecipe as BasePyjniusRecipe


class PyjniusRecipe(BasePyjniusRecipe):
    # Use the latest pyjnius release to avoid Cython 3 incompatibilities
    version = "1.7.0"
    url = "https://github.com/kivy/pyjnius/archive/{version}.zip"
    patches = BasePyjniusRecipe.patches + ["cython3-long-alias.patch"]


recipe = PyjniusRecipe()
