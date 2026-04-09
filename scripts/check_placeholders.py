"""
Verifica que los placeholders en las traducciones ES/EN coincidan
"""
import re
import sys
sys.path.insert(0, '.')

from utils.i18n import TRANSLATIONS

def extract_placeholders(text):
    """Extrae todos los placeholders {variable} de un string"""
    return set(re.findall(r'\{(\w+)\}', text))

def main():
    mismatches = []
    
    for key, value_es in TRANSLATIONS['es'].items():
        if key not in TRANSLATIONS['en']:
            continue
        
        value_en = TRANSLATIONS['en'][key]
        
        placeholders_es = extract_placeholders(value_es)
        placeholders_en = extract_placeholders(value_en)
        
        if placeholders_es != placeholders_en:
            mismatches.append({
                'key': key,
                'es': placeholders_es,
                'en': placeholders_en,
                'missing_in_en': placeholders_es - placeholders_en,
                'missing_in_es': placeholders_en - placeholders_es
            })
    
    if mismatches:
        print(f"⚠️ Se encontraron {len(mismatches)} desajustes en placeholders:\n")
        for m in mismatches[:20]:
            print(f"Key: {m['key']}")
            print(f"  ES: {m['es']}")
            print(f"  EN: {m['en']}")
            if m['missing_in_en']:
                print(f"  ❌ Faltan en EN: {m['missing_in_en']}")
            if m['missing_in_es']:
                print(f"  ❌ Faltan en ES: {m['missing_in_es']}")
            print()
        
        if len(mismatches) > 20:
            print(f"... y {len(mismatches) - 20} más")
    else:
        print("✅ Todos los placeholders coinciden entre español e inglés!")

if __name__ == '__main__':
    main()
