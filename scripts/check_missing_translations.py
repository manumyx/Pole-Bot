#!/usr/bin/env python3
"""Script para encontrar traducciones faltantes en i18n.py"""

import re

with open('utils/i18n.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Extraer sección española
es_section = content.split("'es': {")[1].split("'en': {")[0]
# Extraer sección inglesa
en_section = content.split("'en': {")[1].split("}\n}")[0]

# Encontrar todas las keys
es_keys = set(re.findall(r"'([a-z_\.]+)':\s*['\"]", es_section))
en_keys = set(re.findall(r"'([a-z_\.]+)':\s*['\"]", en_section))

# Keys que faltan en inglés
missing_in_en = sorted(es_keys - en_keys)

# Keys que faltan en español
missing_in_es = sorted(en_keys - es_keys)

print(f"📊 RESUMEN DE TRADUCCIONES:")
print(f"   Keys en español: {len(es_keys)}")
print(f"   Keys en inglés: {len(en_keys)}")
print(f"")

if missing_in_en:
    print(f"❌ Faltan {len(missing_in_en)} keys en INGLÉS:")
    for key in missing_in_en:
        # Buscar el valor en español
        match = re.search(rf"'{key}':\s*['\"]([^'\"]+)['\"]", es_section)
        es_value = match.group(1) if match else "???"
        print(f"   - {key}")
        print(f"     ES: {es_value}")
    print()

if missing_in_es:
    print(f"⚠️ Faltan {len(missing_in_es)} keys en ESPAÑOL:")
    for key in missing_in_es:
        match = re.search(rf"'{key}':\s*['\"]([^'\"]+)['\"]", en_section)
        en_value = match.group(1) if match else "???"
        print(f"   - {key}")
        print(f"     EN: {en_value}")
    print()

if not missing_in_en and not missing_in_es:
    print("✅ ¡Todas las keys están balanceadas entre español e inglés!")
