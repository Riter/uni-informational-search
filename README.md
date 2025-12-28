# Информационный поиск

Студент: Иванов Илья Михайлович (М80-407Б-22)

## Подготовка окружения
- Установить зависимости Python: `python -m pip install -r requirements.txt`
- Собрать C++ бинарники (токенайзер и булев поиск):
  - `cd lab3_text/cpp && make`
  - `cd ../../lab4_bool && make`

## Лабораторная 1: корпус
- Хабр: `python lab1_corpus/corpus_habr.py --output habr.jsonl --limit 30000`
- RIA sitemap → JSONL: `python lab1_corpus/corpus_ria.py --input ria_sitemap.xml --output ria.jsonl`
- Объединение: `python lab1_corpus/corpus_merge.py --inputs habr.jsonl ria.jsonl --output corpus.jsonl`
- Статистика: `python lab1_corpus/corpus_stats.py --input corpus.jsonl --report corpus_stats.json`

## Лабораторная 2: поисковый робот
- Запуск с конфигом: `python lab2_crawler/run_crawler.py lab2_crawler/config.yaml`
- Настройте `config.yaml` (Mongo URI, домены, задержки). Frontier/документы хранятся в Mongo и переживают рестарт.

## Лабораторная 3: токенизация, Ципф, стемминг ( булев индекс и поиск)
- Экспорт текста из корпуса: `python lab1_corpus/jsonl_to_text.py --input corpus.jsonl --output plain.txt`
- Токенизация C++: `cd lab3_text/cpp && ./tokenizer ../plain.txt ../tokens.txt --stats`
- Частоты и Zipf-график: `python lab3_text/token_freq.py --tokens tokens.txt --csv freq.csv --plot zipf_plot.png --report token_report.json`
- Построить индекс напрямую из `corpus.jsonl`: `cd lab4_bool && ./builder ../corpus.jsonl ../index.bin` (добавьте `--nostem`, чтобы отключить стемминг)
- Поиск: `cd lab4_bool && ./bsearch ../index.bin` и вводите запросы вида `term1 AND term2 OR NOT term3`

## Полный пайплайн (пример)
```bash
python lab1_corpus/corpus_habr.py --output habr.jsonl
python lab1_corpus/corpus_ria.py --input ria_sitemap.xml --output ria.jsonl
python lab1_corpus/corpus_merge.py --inputs habr.jsonl ria.jsonl --output corpus.jsonl
python lab1_corpus/jsonl_to_text.py --input corpus.jsonl --output plain.txt
cd lab3_text/cpp && ./tokenizer ../plain.txt ../tokens.txt --stats && cd ../../
python lab3_text/token_freq.py --tokens tokens.txt --csv freq.csv --plot zipf_plot.png
cd lab4_bool && ./builder ../corpus.jsonl ../index.bin && ./bsearch ../index.bin
```
