import re

# Leer el archivo
with open('script_jira.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Diccionario de reemplazos de emojis
emoji_replacements = {
    '🚀': '[INIT]',
    '🔍': '[VALIDANDO]',
    '❌': '[ERROR]',
    '✅': '[OK]',
    '⚠️': '[WARNING]',
    '📊': '[STATS]',
    '📦': '[BLOQUE]',
    '📋': '[JQL]',
    '📄': '[PAGINA]',
    '📁': '[ARCHIVO]',
    '📡': '[STATUS]',
    '⏳': '[WAIT]',
    '🏁': '[COMPLETADO]',
    '🔄': '[PROCESANDO]',
    '🎯': '[EXTRACCION]',
    '💾': '[GUARDANDO]',
    '📈': '[ESTADISTICAS]',
    '📘': '[CATALOGO]',
    '🎉': '[EXITO]'
}

# Reemplazar todos los emojis
for emoji, replacement in emoji_replacements.items():
    content = content.replace(emoji, replacement)

# Guardar el archivo limpio
with open('script_jira.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Emojis reemplazados exitosamente")