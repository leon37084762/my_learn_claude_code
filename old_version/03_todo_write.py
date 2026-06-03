#!/usr/bin/env python3
# Harness: planning -- keep the current session plan outside the model's head.
"""
s03_todo_write.py - Session Planning with TodoWrite

This chapter is about a lightweight session plan, not a durable task graph.
The model can rewrite its current plan, keep one active step in focus, and get
nudged if it stops refreshing the plan for too many rounds.
"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from openai import OpenAI
import json
# 加载配置文件
with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r', encoding='utf-8') as f:
    config = json.load(f)

client = OpenAI(
    base_url=config["base_url"],
    api_key=config["api_key"]
)

WORKDIR = Path.cwd()
MODEL = config["model"]
PLAN_REMINDER_INTERVAL = 3

SYSTEM = f"""
You are a coding agent at {WORKDIR}.
Use the todo tool for multi-step work.
Keep exactly on step in_process when a task has multiple steps.
Refresh the plan as work advances.Prefer tools over prose.
"""

@dataclass
class PlanItem:
    content:str
    status:str = "pending"
    active_form:str = ""

@dataclass
class PlaningState:
    items:list[PlanItem] = field(default_factory=list)
    rounds_since_update:int = 0

class TodoManager:
    def __init__(self):
        self.state = PlaningState()
    def update(self,items:list) ->str:
        if len(items) > 12:
            raise ValueError("Keep the session plan short (max 12 items)")
        normalized = []
        in_progress_count = 0
        for index,raw_item in enumerate(items):
            content = str(raw_item.get("content","")).strip()
            status = str(raw_item.get("status","pending")).lower()
            active_form = str(raw_item.get("activeForm","")).strip()

            if not content:
                raise ValueError(f"Plan item {index+1} is empty")
            if status not in("pending","in_progress","completed"):
                raise ValueError(f"Plan item {index+1} has invalid status: {status}")
            if status == "in_progress":
                in_progress_count += 1

            normalized.append(PlanItem(
                content=content,
                status=status,
                active_form=active_form
            ))
        if in_progress_count > 1:
            raise ValueError("Only one plan item can be in progress")
        
        self.state.items = normalized
        self.state.rounds_since_update = 0
        return self.render()
    def note_rounde_without_update(self) ->None:
        self.state.rounds_since_update += 1
    def reminder(self) ->str | None:
        if not self.state.items:
            return None
        if self.state.rounds_since_update < PLAN_REMINDER_INTERVAL:
            return None
        return "<reminder> Refresh your current plan before continuing.</reminder>"
    def render(self) ->str:
        if not self.state.items:
            return "No session plan yet."

TODO = TodoManager()
def safe_path(path_str:str) -> Path:
    path = (WORKDIR / path_str).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {path_str}")
    return path
def run_bash(command:str) -> str:
