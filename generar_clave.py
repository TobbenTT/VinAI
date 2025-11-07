from werkzeug.security import generate_password_hash

# ▼▼▼ CAMBIA ESTO ▼▼▼
nueva_clave = "654321"
# ▲▲▲ CAMBIA ESTO ▲▲▲

hash_generado = generate_password_hash(nueva_clave)

print("\n¡Copia la siguiente línea completa!:\n")
print(hash_generado)
print("\n")