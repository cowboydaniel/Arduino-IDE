from pythonforandroid.recipes.libffi import LibffiRecipe


class LibffiRecipePinned(LibffiRecipe):
    """
    Custom libffi recipe with patch to fix obsolete LT_SYS_SYMBOL_USCORE macro.

    The patch file in patches/remove-obsolete-macro.patch is automatically
    applied by python-for-android before building.

    This fixes the autoreconf error:
    "configure.ac:228: error: possibly undefined macro: LT_SYS_SYMBOL_USCORE"
    """
    pass


recipe = LibffiRecipePinned()
