from pythonforandroid.recipes.libffi import LibffiRecipe
from pythonforandroid.util import current_directory
from os.path import join
import sh


class LibffiRecipePinned(LibffiRecipe):
    """
    Custom libffi recipe that patches configure.ac to remove obsolete macros
    before running autoreconf.

    This fixes the error: "possibly undefined macro: LT_SYS_SYMBOL_USCORE"
    """

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)

        with current_directory(self.get_build_dir(arch.arch)):
            # Patch configure.ac to remove obsolete LT_SYS_SYMBOL_USCORE macro
            configure_ac_path = join(self.get_build_dir(arch.arch), 'configure.ac')

            try:
                with open(configure_ac_path, 'r') as f:
                    content = f.read()

                # Comment out the obsolete LT_SYS_SYMBOL_USCORE macro
                # This macro is deprecated and not present in modern libtool
                if 'LT_SYS_SYMBOL_USCORE' in content:
                    self.logger.info('Patching configure.ac to remove obsolete LT_SYS_SYMBOL_USCORE macro')
                    content = content.replace('LT_SYS_SYMBOL_USCORE',
                                            'dnl LT_SYS_SYMBOL_USCORE (removed - obsolete macro)')

                    with open(configure_ac_path, 'w') as f:
                        f.write(content)
                    self.logger.info('Successfully patched configure.ac')
            except Exception as e:
                self.logger.warning(f'Could not patch configure.ac: {e}')

        # Call the parent class build method
        super().build_arch(arch)


recipe = LibffiRecipePinned()
