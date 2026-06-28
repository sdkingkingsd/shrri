import os
import re
from datetime import datetime

SKILLS_DIR = os.path.expanduser('~/shrri/skills')

def ensure_skills_dir():
    os.makedirs(SKILLS_DIR, exist_ok=True)

def skill_path(name):
    return os.path.join(SKILLS_DIR, name, 'SKILL.md')

def list_skills():
    ensure_skills_dir()
    skills = []
    for item in os.listdir(SKILLS_DIR):
        p = os.path.join(SKILLS_DIR, item, 'SKILL.md')
        if os.path.exists(p):
            with open(p) as f:
                content = f.read()
            desc = ''
            for line in content.splitlines():
                if line.startswith('description:'):
                    desc = line.replace('description:', '').strip()
                    break
            skills.append({'name': item, 'description': desc})
    return skills

def load_skill(name):
    p = skill_path(name)
    if os.path.exists(p):
        with open(p) as f:
            return f.read()
    return ''

def find_relevant_skill(message):
    ensure_skills_dir()
    msg_words = set(w.lower() for w in message.split() if len(w) > 3)
    if not msg_words:
        return ''
    best_match = None
    best_score = 0
    for item in os.listdir(SKILLS_DIR):
        p = os.path.join(SKILLS_DIR, item, 'SKILL.md')
        if not os.path.exists(p):
            continue
        with open(p) as f:
            content = f.read()
        skill_words = set(w.lower() for w in content.split() if len(w) > 3)
        score = len(msg_words & skill_words)
        if score > best_score:
            best_score = score
            best_match = (item, content)
    if best_match and best_score >= 2:
        return best_match[1]
    return ''

def create_skill(name, description, procedure, example_input, example_output, category='general'):
    ensure_skills_dir()
    skill_dir = os.path.join(SKILLS_DIR, name)
    os.makedirs(skill_dir, exist_ok=True)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = []
    lines.append('---')
    lines.append('name: ' + name)
    lines.append('description: ' + description)
    lines.append('category: ' + category)
    lines.append('version: 1.0')
    lines.append('use_count: 1')
    lines.append('created: ' + now)
    lines.append('---')
    lines.append('')
    lines.append('## When to Use')
    lines.append(example_input[:200])
    lines.append('')
    lines.append('## Procedure')
    lines.append(procedure)
    lines.append('')
    lines.append('## Example Output')
    lines.append(example_output[:200])
    lines.append('')
    lines.append('## Notes')
    lines.append('- Auto-created by SHRRI')
    lines.append('- Last updated: ' + now)
    with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
        f.write('\n'.join(lines))
    return skill_dir

def improve_skill(name, new_note):
    p = skill_path(name)
    if not os.path.exists(p):
        return False
    with open(p) as f:
        content = f.read()
    content = re.sub(r'use_count: (\d+)', lambda m: 'use_count: ' + str(int(m.group(1))+1), content)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    content = re.sub(r'Last updated:.*', 'Last updated: ' + now, content)
    if new_note:
        content += '\n- Improved: ' + new_note
    with open(p, 'w') as f:
        f.write(content)
    return True

def increment_use_count(name):
    p = skill_path(name)
    if not os.path.exists(p):
        return
    with open(p) as f:
        content = f.read()
    content = re.sub(r'use_count: (\d+)', lambda m: 'use_count: ' + str(int(m.group(1))+1), content)
    with open(p, 'w') as f:
        f.write(content)

def auto_create_from_interaction(message, response, agent_used, conn):
    if len(message.split()) < 2 or len(response.split()) < 3:
        return None
    skip_agents = {'chat', 'unknown'}
    if agent_used in skip_agents:
        return None
    existing = find_relevant_skill(message)
    if existing:
        return None
    keywords = [w.lower() for w in message.split() if len(w) > 4][:3]
    skill_name = agent_used + '-' + '-'.join(keywords) if keywords else agent_used
    skill_name = re.sub(r'[^a-z0-9-]', '', skill_name)[:40]
    procedure = '1. User asks: ' + message[:100] + '\n2. Tool used: ' + agent_used + '\n3. Steps: detect intent -> run tool -> format response\n4. Return result to user'
    create_skill(
        name=skill_name,
        description='Handle ' + agent_used + ' requests like: ' + message[:60],
        procedure=procedure,
        example_input=message[:200],
        example_output=response[:200],
        category=agent_used
    )
    try:
        conn.execute('''INSERT INTO skills (skill_name, description, example_input, example_output, timestamp) VALUES (?, ?, ?, ?, ?) ON CONFLICT(skill_name) DO UPDATE SET use_count=use_count+1''',
            (skill_name, 'Handle ' + agent_used + ' requests', message[:200], response[:200], datetime.now().isoformat()))
        conn.commit()
    except Exception:
        pass
    return skill_name
def improve_skill_from_correction(message, correction_text, conn):
    """When user corrects SHRRI, find related skill and improve it."""
    # Find the most relevant skill for this message
    existing = find_relevant_skill(message)
    if not existing:
        return None
    # Extract skill name from content
    skill_name = None
    for line in existing.splitlines():
        if line.startswith('name:'):
            skill_name = line.replace('name:', '').strip()
            break
    if not skill_name:
        return None
    # Add correction as a note to improve the skill
    p = skill_path(skill_name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        skill_content = f.read()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    correction_note = '\n- Correction [' + now + ']: ' + correction_text[:200]
    # Add pitfalls section if not exists
    if '## Pitfalls' not in skill_content:
        skill_content += '\n\n## Pitfalls\n- Never repeat this mistake: ' + correction_text[:200]
    else:
        skill_content += correction_note
    # Update version
    import re
    skill_content = re.sub(r'version: (\d+)\.(\d+)', lambda m: 'version: ' + m.group(1) + '.' + str(int(m.group(2))+1), skill_content)
    skill_content = re.sub(r'Last updated:.*', 'Last updated: ' + now, skill_content)
    with open(p, 'w') as f:
        f.write(skill_content)
    # Also update DB
    try:
        conn.execute("UPDATE skills SET description=description || ' [corrected]' WHERE skill_name=?", (skill_name,))
        conn.commit()
    except Exception:
        pass
    return skill_name

def detect_and_save_patterns(conn):
    """Mine conversation history to find recurring patterns and save as skills."""
    try:
        rows = conn.execute(
            "SELECT content, timestamp FROM conversations WHERE role='user' ORDER BY id DESC LIMIT 100"
        ).fetchall()
    except Exception:
        return []

    from collections import Counter
    import re

    # Count recurring intents
    tool_counts = Counter()
    time_patterns = []

    for content, timestamp in rows:
        msg = content.lower()
        # Detect tool patterns
        if any(w in msg for w in ['gmail', 'mail', 'email']):
            tool_counts['gmail'] += 1
        if any(w in msg for w in ['whatsapp', 'message', 'chat']):
            tool_counts['whatsapp'] += 1
        if any(w in msg for w in ['reminder', 'remind', 'alarm']):
            tool_counts['reminder'] += 1
        if any(w in msg for w in ['weather', 'temperature', 'rain']):
            tool_counts['weather'] += 1
        if any(w in msg for w in ['calendar', 'schedule', 'event']):
            tool_counts['calendar'] += 1

        # Detect time patterns
        time_match = re.search(r'(\d+:\d+\s*(?:am|pm)?)', msg)
        if time_match:
            time_patterns.append(time_match.group(1))

    created = []
    # Create habit skills for tools used 3+ times
    for tool, count in tool_counts.items():
        if count >= 3:
            skill_name = 'habit-' + tool
            p = skill_path(skill_name)
            if not os.path.exists(p):
                time_hint = ''
                if time_patterns:
                    from collections import Counter as C
                    common_time = C(time_patterns).most_common(1)[0][0]
                    time_hint = ' Usually around ' + common_time + '.'
                create_skill(
                    name=skill_name,
                    description='Shrridharshan frequently checks ' + tool + ' (' + str(count) + ' times).' + time_hint,
                    procedure='1. Auto-detected habit: user checks ' + tool + ' regularly\n2. Pre-load ' + tool + ' tool\n3. Return latest data immediately',
                    example_input='check ' + tool,
                    example_output='Fetched ' + tool + ' data',
                    category='habit'
                )
                created.append(skill_name)
    return created
