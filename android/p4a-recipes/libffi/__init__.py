from pythonforandroid.recipes.libffi import LibffiRecipe
from os.path import join


class LibffiRecipePinned(LibffiRecipe):
    """
    Custom libffi recipe that patches configure.ac to fix obsolete LT_SYS_SYMBOL_USCORE macro.

    This fixes the autoreconf error:
    "configure.ac:XXX: error: possibly undefined macro: LT_SYS_SYMBOL_USCORE"

    The macro is obsolete and not present in modern libtool versions.
    """

    def build_arch(self, arch):
        """Override build to patch configure.ac before running parent's build_arch"""

        # Patch configure.ac before the parent class runs autoreconf
        configure_ac = join(self.get_build_dir(arch.arch), 'configure.ac')

        try:
            with open(configure_ac, 'r') as f:
                content = f.read()

            # Replace the obsolete LT_SYS_SYMBOL_USCORE macro
            # Set sys_symbol_underscore to 'no' (safe default for modern systems)
            if 'LT_SYS_SYMBOL_USCORE' in content:
                self.logger.info('Patching configure.ac to remove obsolete LT_SYS_SYMBOL_USCORE macro')

                # Replace the macro call with a comment and direct assignment
                content = content.replace(
                    'LT_SYS_SYMBOL_USCORE',
                    '# LT_SYS_SYMBOL_USCORE - obsolete macro removed\nsys_symbol_underscore=no'
                )

                with open(configure_ac, 'w') as f:
                    f.write(content)

                self.logger.info('Successfully patched configure.ac')
            else:
                self.logger.info('LT_SYS_SYMBOL_USCORE not found in configure.ac')

        except Exception as e:
            self.logger.warning(f'Could not patch configure.ac: {e}')

        # Call the parent class build method which will run autoreconf, configure, and make
        super().build_arch(arch)


recipe = LibffiRecipePinned()

