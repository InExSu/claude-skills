#!/bin/bash
[ -z "$1" ] && echo "Использование: $0 \"Сообщение коммита\"" && exit 1

# Добавляем ВСЕ изменения
git add -A . && \
git commit -m "$1" && \
git push

<<COMMENT
find . -name "*.sh" -exec chmod +x {} +
for file in *.sh; do dos2unix "$file"; done
COMMENT