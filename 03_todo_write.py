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
        
