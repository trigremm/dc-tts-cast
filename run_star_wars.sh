#!/usr/bin/env bash
set -uo pipefail

SRC_ROOT=/workspace/trigremm/pybookworm/output/star_wars
DST_ROOT=/workspace/trigremm/dc-tts-cast/output
SPEAKER=baya
SPEED=1.5

cd /workspace/trigremm/dc-tts-cast

docker_alive() {
    docker info >/dev/null 2>&1
}

# Без этой проверки упавший демон выглядит как отказ каждой книги по очереди:
# 15.05.2026 так молча сгорели 19 книг за одну секунду, а скрипт отчитался ALL DONE.
if ! docker_alive; then
    echo "[abort] docker daemon недоступен — запусти Docker Desktop и повтори"
    exit 1
fi

fail_count=0
ok_count=0

for book_dir in "$SRC_ROOT"/*/; do
    slug=$(basename "$book_dir")
    out="$DST_ROOT/star_wars_${slug}_${SPEAKER}"

    txt_count=$(find "$book_dir" -maxdepth 1 -name '*_chapter.txt' | wc -l)
    if [[ "$txt_count" -eq 0 ]]; then
        echo "[skip] $slug — no chapter .txt files"
        continue
    fi

    if [[ -f "$out/tts_config.json" ]] && [[ -n "$(find "$out" -maxdepth 1 -name '*.mp3' -print -quit)" ]]; then
        # already has config AND at least one mp3 → assume finished or use run-resume manually
        mp3_count=$(find "$out" -maxdepth 1 -name '*.mp3' | wc -l)
        if [[ "$mp3_count" -ge "$txt_count" ]]; then
            echo "[skip] $slug — $mp3_count/$txt_count mp3s already present"
            continue
        fi
        echo "==== $(date '+%F %T') RESUME $slug ($mp3_count/$txt_count) ===="
        if make run-resume OUTPUT_HOST="$out"; then
            ok_count=$((ok_count + 1))
        else
            fail_count=$((fail_count + 1))
            echo "[fail] $slug — run-resume returned non-zero"
            if ! docker_alive; then
                echo "==== $(date '+%F %T') ABORT: docker daemon пропал на $slug (ok=$ok_count fail=$fail_count) ===="
                exit 1
            fi
        fi
        echo "==== $(date '+%F %T') END    $slug ===="
        continue
    fi

    # clean up stale config from a previously-failed empty-dir attempt
    if [[ -d "$out" ]] && [[ -z "$(find "$out" -maxdepth 1 -name '*.mp3' -print -quit)" ]]; then
        rm -f "$out/tts_config.json"
    fi

    echo "==== $(date '+%F %T') BEGIN  $slug ($txt_count chapters) ===="
    if make run \
        SPEAKER="$SPEAKER" \
        SPEED="$SPEED" \
        INPUT_HOST="$book_dir" \
        OUTPUT_HOST="$out" \
        ALBUM="Star Wars — $slug"; then
        ok_count=$((ok_count + 1))
    else
        fail_count=$((fail_count + 1))
        echo "[fail] $slug — make run returned non-zero"
        if ! docker_alive; then
            echo "==== $(date '+%F %T') ABORT: docker daemon пропал на $slug (ok=$ok_count fail=$fail_count) ===="
            exit 1
        fi
    fi
    echo "==== $(date '+%F %T') END    $slug ===="
done

echo "==== $(date '+%F %T') ALL DONE: ok=$ok_count fail=$fail_count ===="
