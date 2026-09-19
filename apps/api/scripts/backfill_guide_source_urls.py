"""가이드 출처 URL 백필 (seed_guides 는 기존 문서를 건너뛴다).

``seed_guides`` 는 slug 가 이미 있으면 문서도 출처도 만들지 않는다. 그래서 시드 파일에
URL 을 나중에 채워 넣어도 **이미 적재된 DB 에는 반영되지 않는다.** 이 스크립트가 그
간극만 메운다.

- 정본은 ``seed_guides.GUIDE_DOCUMENTS`` 하나다. 여기에 URL 을 다시 적지 않는다 —
  두 곳에 적으면 갈라진다.
- 매칭 키는 ``(문서 slug, source_name)``. 출처 이름이 바뀌면 매칭이 끊기고 경고가 뜬다.
- **덮어쓰지 않는다.** 이미 값이 있고 시드와 다르면 건드리지 않고 불일치로 보고한다 —
  운영에서 손으로 고친 값을 조용히 되돌리지 않기 위해서다.
- 기본 dry-run, ``--apply`` 로 반영.

실행:
    uv run python -m scripts.backfill_guide_source_urls            # dry-run
    uv run python -m scripts.backfill_guide_source_urls --apply    # 반영
"""

import sys

from sqlalchemy import select

from app.db.models import GuideDocument, GuideDocumentSource
from app.db.session import SessionLocal
from scripts.seed_guides import GUIDE_DOCUMENTS


def main() -> None:
    apply = "--apply" in sys.argv[1:]

    # (slug, source_name) → url — 시드가 URL 을 정한 출처만 모은다.
    wanted = {
        (slug, name): url
        for slug, _title, _cat, _verified, sources in GUIDE_DOCUMENTS
        for name, url, _note in sources
        if url is not None
    }

    with SessionLocal() as db:
        rows = db.execute(
            select(GuideDocumentSource, GuideDocument.slug).join(
                GuideDocument, GuideDocumentSource.guide_document_id == GuideDocument.id
            )
        ).all()

        filled = skipped = 0
        conflicts: list[str] = []
        seen: set[tuple[str, str]] = set()

        for source, slug in rows:
            key = (slug, source.source_name)
            url = wanted.get(key)
            if url is None:
                continue
            seen.add(key)

            if source.source_url == url:
                skipped += 1
                continue
            if source.source_url is not None:
                conflicts.append(
                    f"  ⚠️ {slug} / {source.source_name}\n"
                    f"     DB   {source.source_url}\n"
                    f"     시드 {url}"
                )
                continue

            filled += 1
            print(f"  {slug} / {source.source_name}\n     → {url}")
            if apply:
                source.source_url = url

        missing = sorted(wanted.keys() - seen)
        if apply:
            db.commit()

        print(f"\n  채움 {filled}건 / 이미 동일 {skipped}건")
        if conflicts:
            print(f"\n  DB 값이 시드와 다름 {len(conflicts)}건 — 건드리지 않았습니다:")
            print("\n".join(conflicts))
        if missing:
            print(f"\n  ⚠️ DB 에서 못 찾은 출처 {len(missing)}건 (이름이 바뀌었거나 미적재):")
            for slug, name in missing:
                print(f"     {slug} / {name}")
        if not apply:
            print("\n  dry-run 입니다. 반영하려면 --apply 를 붙이세요.")


if __name__ == "__main__":
    main()
