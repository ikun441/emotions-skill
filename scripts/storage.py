"""持久化：人格档案 JSON 原子读写。"""
from __future__ import annotations

import json
import os
from pathlib import Path

from models import PersonalityProfile


class Storage:
    def __init__(self, profiles_dir: str | Path | None = None):
        if profiles_dir is None:
            env_dir = os.environ.get("EMOTIONS_PROFILES_DIR")
            if env_dir:
                profiles_dir = Path(env_dir)
            else:
                project_root = Path(__file__).parent.parent
                profiles_dir = project_root / "data" / "profiles"
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, profile_id: str) -> Path:
        return self.profiles_dir / f"{profile_id}.json"

    def load(self, profile_id: str) -> PersonalityProfile:
        with open(self._path(profile_id), "r", encoding="utf-8") as f:
            return PersonalityProfile.from_dict(json.load(f))

    def save(self, profile: PersonalityProfile) -> None:
        path = self._path(profile.profile_id)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def append_history(self, profile: PersonalityProfile, entry) -> None:
        profile.history.append(entry)
        limit = profile.config.history_limit
        if len(profile.history) > limit:
            profile.history = profile.history[-limit:]
        self.save(profile)

    def exists(self, profile_id: str) -> bool:
        return self._path(profile_id).exists()

    def list_profiles(self) -> list[str]:
        return [p.stem for p in self.profiles_dir.glob("*.json")]

    def delete(self, profile_id: str) -> None:
        path = self._path(profile_id)
        if path.exists():
            os.remove(path)