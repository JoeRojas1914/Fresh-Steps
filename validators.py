import re

_RE_CORREO   = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
_RE_TELEFONO = re.compile(r'^[0-9]{10}$')
_RE_PIN      = re.compile(r'^[0-9]{4,6}$')


def validar_correo(correo: str | None) -> str | None:
    if not correo or not correo.strip():
        return None
    correo = correo.strip()
    if not _RE_CORREO.match(correo):
        raise ValueError(f"Correo inválido: '{correo}'")
    return correo


def validar_telefono(telefono: str | None) -> str | None:
    if not telefono or not telefono.strip():
        return None
    telefono = re.sub(r'[\s\-\(\)]', '', telefono.strip())
    if not _RE_TELEFONO.match(telefono):
        raise ValueError("El teléfono debe tener exactamente 10 dígitos")
    return telefono


def validar_nombre(nombre: str | None, campo: str = "Nombre") -> str:
    if not nombre or not nombre.strip():
        raise ValueError(f"{campo} es obligatorio")
    nombre = nombre.strip()
    if len(nombre) > 100:
        raise ValueError(f"{campo} no puede tener más de 100 caracteres")
    return nombre


def validar_pin(pin: str | None) -> str | None:
    if not pin or not pin.strip():
        return None
    if not _RE_PIN.match(pin.strip()):
        raise ValueError("El PIN debe tener entre 4 y 6 dígitos numéricos")
    return pin.strip()


def validar_password(password: str | None, obligatorio: bool = False) -> str | None:
    if not password or not password.strip():
        if obligatorio:
            raise ValueError("La contraseña es obligatoria")
        return None
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r'[A-Z]', password):
        raise ValueError("La contraseña debe contener al menos una mayúscula")
    if not re.search(r'\d', password):
        raise ValueError("La contraseña debe contener al menos un número")
    return password
