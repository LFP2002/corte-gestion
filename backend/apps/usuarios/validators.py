from django.core.exceptions import ValidationError


class PoliticaPasswordValidator:
    """Política para nuevas credenciales; no interviene en comprobar hashes existentes."""

    def validate(self, password, user=None):
        requisitos = (
            (len(password) >= 8, 'Debe contener al menos 8 caracteres.', 'longitud'),
            (any(c.isupper() for c in password), 'Debe contener al menos una letra mayúscula.', 'mayuscula'),
            (any(c.islower() for c in password), 'Debe contener al menos una letra minúscula.', 'minuscula'),
            (any(c.isdecimal() for c in password), 'Debe contener al menos un número.', 'numero'),
            (any(not c.isalnum() and not c.isspace() for c in password),
             'Debe contener al menos un símbolo o carácter especial (no un espacio).', 'simbolo'),
        )
        errores = [ValidationError(mensaje, code=f'password_{codigo}')
                   for cumple, mensaje, codigo in requisitos if not cumple]
        if errores:
            raise ValidationError(errores)

    def get_help_text(self):
        return 'Mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo; un espacio no cuenta como símbolo.'
