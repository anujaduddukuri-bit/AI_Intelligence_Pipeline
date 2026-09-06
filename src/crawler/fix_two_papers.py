import json
from pathlib import Path


OUTPUT_FILE = Path(
    "data/raw/research_papers_github.json"
)


records_to_add = [
    {
        "schemaVersion": "1.0",
        "recordType": "RESEARCH_PAPER",
        "title": "On the Texture Bias for Few-Shot CNN Segmentation",
        "authors": [
            "Reza Azad",
            "Abdur R. Fayjie",
            "Claude Kauffman",
            "Ismail Ben Ayed",
            "Marco Pedersoli",
            "Jose Dolz"
        ],
        "paper_url": "https://arxiv.org/abs/2003.04052v3",
        "github_url": "https://github.com/Scout-UCAS/fewshot-segmentation",
        "github_stars": 1,
        "published_date": "2020-03-06",
        "arxiv_id": "2003.04052",
        "github_forks": 0,
        "github_watchers": 0,
        "github_match_verified": True,
        "github_verification_note": (
            "Current GitHub fork of the repository; "
            "README identifies the exact paper."
        )
    },
    {
        "schemaVersion": "1.0",
        "recordType": "RESEARCH_PAPER",
        "title": "Diffusion-based Reinforcement Learning for Edge-enabled AI-Generated Content Services",
        "authors": [
            "Hongyang Du",
            "Zonghang Li",
            "Dusit Niyato",
            "Jiawen Kang",
            "Zehui Xiong",
            "Huawei Huang",
            "Shiwen Mao"
        ],
        "paper_url": "https://arxiv.org/abs/2303.13052v3",
        "github_url": "https://github.com/HongyangDu/AGOD",
        "github_stars": 8,
        "published_date": "2023-03-23",
        "arxiv_id": "2303.13052",
        "github_forks": 1,
        "github_watchers": 0,
        "github_match_verified": True,
        "github_verification_note": (
            "Current repository README identifies the exact paper "
            "and describes it as the implementation."
        )
    }
]


def main():

    if OUTPUT_FILE.exists():

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            records = json.load(f)

    else:

        records = []

    existing_ids = {
        str(record.get("arxiv_id", "")).strip()
        for record in records
    }

    added = 0

    for record in records_to_add:

        arxiv_id = record["arxiv_id"]

        if arxiv_id in existing_ids:

            print(
                f"Already exists: {arxiv_id}"
            )

            continue

        records.append(record)

        existing_ids.add(arxiv_id)

        added += 1

        print(
            f"Added: {arxiv_id}"
        )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("RESEARCH PAPER DATASET UPDATED")
    print("=" * 60)
    print(
        f"Records added: {added}"
    )
    print(
        f"Total records: {len(records)}"
    )

    if len(records) >= 1000:
        print("SUCCESS: Minimum 1,000 papers reached.")


if __name__ == "__main__":
    main()