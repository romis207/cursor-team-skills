# Cursor Team Skills

סקילים משותפים ל-Cursor Agent עבור הצוות.

Repo: [github.com/romis207/cursor-team-skills](https://github.com/romis207/cursor-team-skills)

---

## התקנה (פעם אחת לכל משתמש)

### 1. Clone

```bash
git clone git@github.com:romis207/cursor-team-skills.git ~/cursor-team-skills
```

> צריך SSH key רשום ב-GitHub. אם ה-repo Private — המנהלת מוסיפה אותך ב-**Settings → Collaborators**.

### 2. קישור ל-Cursor

```bash
bash ~/cursor-team-skills/install.sh
```

הסקריפט יוצר symlink לכל סקיל:

```
~/.cursor/skills/bulk-etc-change -> ~/cursor-team-skills/bulk-etc-change
```

### 3. הפעלה מחדש

סגרי ופתחי Cursor (או צ'אט חדש).

### 4. בדיקה

בצ'אט:

```
/bulk-etc-change
```

---

## עדכון (כשמישהו דחף שינוי)

```bash
cd ~/cursor-team-skills
git pull
```

אין צורך להריץ שוב `install.sh` — ה-symlink מצביע על אותה תיקייה.

אם נוסף **סקיל חדש** (תיקייה חדשה), הריצי `install.sh` פעם אחת:

```bash
bash ~/cursor-team-skills/install.sh
```

---

## עריכה ב-Cursor

פתחי את התיקייה ב-Cursor:

**File → Open Folder →** `~/cursor-team-skills`

ערכי, ואז:

```bash
cd ~/cursor-team-skills
git add .
git commit -m "תיאור השינוי"
git push
```

---

## סקילים זמינים

| סקיל | תיאור |
|------|--------|
| [bulk-etc-change](bulk-etc-change/) | החלפת קבצי ETC ב-bulk לסשני GM (ext_calib.conf, כל 4 ה-views) |

---

## הוספת סקיל חדש

1. צרי תיקייה חדשה עם `SKILL.md` (ראי `bulk-etc-change/` כדוגמה).
2. `git add . && git commit && git push`
3. שאר הצוות: `git pull` + `bash install.sh` (רק לסקיל חדש).

---

## איך זה עובד

```
GitHub (romis207/cursor-team-skills)
        ↓  git clone
~/cursor-team-skills/          ← repo מקומי
        ↓  install.sh
~/.cursor/skills/<skill>/    ← Cursor קורא מכאן
```

**חשוב:** אל תערכי ישירות ב-`~/.cursor/skills/` — ערכי ב-`~/cursor-team-skills/`.
