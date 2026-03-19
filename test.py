import json
import os
import pickle


def migrate_mapdata_json_to_pickle(map_data_dir: str) -> None:
    json_files = [
        os.path.join(map_data_dir, name)
        for name in os.listdir(map_data_dir)
        if name.lower().endswith(".json")
    ]

    migrated = 0
    skipped = 0
    failed = 0

    for json_path in sorted(json_files):
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        pickle_path = os.path.join(map_data_dir, f"{base_name}.pkl")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data_list = json.load(f)

            data_set = set(tuple(p) for p in data_list)

            if os.path.exists(pickle_path):
                skipped += 1
                continue

            tmp_path = f"{pickle_path}.tmp"
            with open(tmp_path, "wb") as f:
                pickle.dump(data_set, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp_path, pickle_path)

            migrated += 1
        except Exception as e:
            failed += 1
            print(f"迁移失败: {json_path} -> {pickle_path} ({e})")

    print(f"迁移完成: migrated={migrated}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    map_data_dir = os.path.join(project_root, "mapData")
    migrate_mapdata_json_to_pickle(map_data_dir)
