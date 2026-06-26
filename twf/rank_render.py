"""TodayWaifu - 今日老婆总排行 HTML 渲染（蓝白·达妮娅主题）。

把 `_total_wife_rank_items` / `_fetch_cloud_total_wife_rank` 产出的
`(count, updated_at, name)` 列表渲染成一张排行榜图片。整体走干净的蓝白配色，
右上角放达妮娅看板娘立绘做视觉主体；前三名用领奖台呈现，其余用带头像和细进度条
的列表行。角色头像优先取本地图片目录里的第一张图，取不到时用按角色名生成的固定
蓝调字母头像兜底，全程不发起任何网络请求。
"""
from __future__ import annotations

from .shared import *  # noqa: F403

# —— 画布与展示参数 ——
RANK_RENDER_WIDTH = 960
RANK_DISPLAY_LIMIT = 18
RANK_PODIUM_SIZE = 3

# 看板娘立绘（达妮娅），放在插件根目录，和 help.png / ICON.png 同级
HERO_IMAGE_PATH = BASE_DIR / 'rank_bg.png'

# 进程内缓存看板娘立绘的 data URI，避免每次渲染都重新读盘+base64
_HERO_CACHE: dict[str, str | None] = {}

# 领奖台前三名主题：金 / 银 / 铜，但整体压低饱和度，贴合蓝白风
_PODIUM_THEME = {
    1: {
        'medal': '①',
        'ring': '#e9c45f',
        'ring_soft': 'rgba(233, 196, 95, 0.30)',
        'accent': '#d7a93a',
        'tag': 'CHAMPION',
    },
    2: {
        'medal': '②',
        'ring': '#9fb3cf',
        'ring_soft': 'rgba(159, 179, 207, 0.30)',
        'accent': '#7e93b4',
        'tag': 'SECOND',
    },
    3: {
        'medal': '③',
        'ring': '#cf9a6a',
        'ring_soft': 'rgba(207, 154, 106, 0.28)',
        'accent': '#b9794a',
        'tag': 'THIRD',
    },
}

# 领奖台底座高度（像素），第一名最高，营造领奖台落差
_PODIUM_BASE_HEIGHT = {1: 70, 2: 48, 3: 38}

# 列表/兜底头像的蓝调配色：(渐变起色, 渐变止色, 文字色)
_FALLBACK_PALETTE = (
    ('#cfe6fb', '#8fc4ee', '#163a63'),
    ('#d6e7fb', '#9bb9ef', '#1b2f5c'),
    ('#cdeaf2', '#82c8de', '#0e3a4b'),
    ('#dbe8fb', '#a7c2f0', '#1d3056'),
    ('#c9e2f7', '#7eb6e8', '#123a60'),
    ('#d2ecf3', '#8fd0e2', '#0f3647'),
    ('#e0e9fb', '#b1c5f0', '#22305a'),
    ('#c6e4ee', '#7cc4d6', '#0d3344'),
)


def _fallback_palette_for(name: str) -> tuple[str, str, str]:
    index = sum(ord(ch) for ch in name) % len(_FALLBACK_PALETTE)
    return _FALLBACK_PALETTE[index]


def _guess_image_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    if suffix == '.webp':
        return 'image/webp'
    if suffix == '.gif':
        return 'image/gif'
    return 'image/png'


def _encode_image_file(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        logger.debug(f'{LOG_PREFIX} 读取图片失败: {path} ({exc})')
        return None
    if not raw:
        return None
    encoded = base64.b64encode(raw).decode('ascii')
    return f'data:{_guess_image_mime(path)};base64,{encoded}'


def _hero_data_uri() -> str | None:
    """读取并缓存达妮娅看板娘立绘的 data URI，文件缺失则返回 None。"""
    key = str(HERO_IMAGE_PATH)
    if key not in _HERO_CACHE:
        if HERO_IMAGE_PATH.is_file():
            _HERO_CACHE[key] = _encode_image_file(HERO_IMAGE_PATH)
        else:
            logger.debug(f'{LOG_PREFIX} 看板娘立绘不存在: {HERO_IMAGE_PATH}')
            _HERO_CACHE[key] = None
    return _HERO_CACHE[key]


def _build_avatar_lookup() -> dict[str, str]:
    """返回 {角色名: data URI} 的本地头像查找表，找不到本地候选图就返回空表。"""
    candidates, error = _load_local_candidates('wife')
    if error or not candidates:
        logger.debug(f'{LOG_PREFIX} 总排行渲染未取到本地角色图片，使用字母头像兜底: {error}')
        return {}

    lookup: dict[str, str] = {}
    for candidate in candidates:
        if candidate.name in lookup or not candidate.images:
            continue
        encoded = _encode_image_file(Path(candidate.images[0]))
        if encoded:
            lookup[candidate.name] = encoded
    return lookup


def _avatar_html(name: str, data_uri: str | None, *, size: int, extra_class: str = '') -> str:
    safe_name = html.escape(name)
    cls = f'avatar {extra_class}'.strip()
    if data_uri:
        return (
            f'<div class="{cls} avatar-img" style="width:{size}px;height:{size}px;">'
            f'<img src="{data_uri}" alt="{safe_name}">'
            f'</div>'
        )
    start, end, ink = _fallback_palette_for(name)
    initial = html.escape(name[:1] or '?')
    return (
        f'<div class="{cls} avatar-fallback" style="width:{size}px;height:{size}px;'
        f'background:linear-gradient(135deg,{start},{end});color:{ink};">'
        f'{initial}</div>'
    )


def _format_updated_at(updated_at: int) -> str:
    if updated_at <= 0:
        return ''
    try:
        return time.strftime('%m-%d', time.localtime(updated_at))
    except (OverflowError, OSError, ValueError):
        return ''


def _build_podium_slot(
    rank: int,
    count: int,
    updated_at: int,
    name: str,
    avatar_lookup: dict[str, str],
    max_count: int,
) -> str:
    theme = _PODIUM_THEME[rank]
    base_height = _PODIUM_BASE_HEIGHT[rank]
    safe_name = html.escape(name)
    avatar_size = 84 if rank == 1 else 66
    avatar = _avatar_html(name, avatar_lookup.get(name), size=avatar_size, extra_class='podium-avatar')
    date_text = _format_updated_at(updated_at)
    date_html = (
        f'<div class="podium-date">最近 {html.escape(date_text)}</div>' if date_text else ''
    )
    share = 0 if max_count <= 0 else round(count / max_count * 100)
    return f'''
        <div class="podium-slot rank-{rank}">
          <div class="podium-medal" style="--accent:{theme['accent']};">{theme['medal']}</div>
          <div class="avatar-ring" style="--ring:{theme['ring']};--ring-soft:{theme['ring_soft']};">
            {avatar}
          </div>
          <div class="podium-name" title="{safe_name}">{safe_name}</div>
          <div class="podium-count"><b>{count}</b> 次</div>
          {date_html}
          <div class="podium-base" style="height:{base_height}px;--accent:{theme['accent']};">
            <span class="podium-tag">{theme['tag']}</span>
            <span class="podium-share">榜首的 {share}%</span>
          </div>
        </div>
    '''


def _build_list_row(
    rank: int,
    count: int,
    updated_at: int,
    name: str,
    avatar_lookup: dict[str, str],
    max_count: int,
) -> str:
    safe_name = html.escape(name)
    avatar = _avatar_html(name, avatar_lookup.get(name), size=42, extra_class='row-avatar')
    width = 4 if max_count <= 0 else max(4, round(count / max_count * 100))
    date_text = _format_updated_at(updated_at)
    date_html = f'<span class="row-date">最近 {html.escape(date_text)}</span>' if date_text else ''
    return f'''
        <div class="list-row">
          <div class="rank-num">{rank}</div>
          {avatar}
          <div class="row-body">
            <div class="row-head">
              <span class="row-name" title="{safe_name}">{safe_name}</span>
              {date_html}
              <span class="row-count">{count} 次</span>
            </div>
            <div class="bar-track"><div class="bar-fill" style="width:{width}%;"></div></div>
          </div>
        </div>
    '''


def _build_hero_html() -> str:
    data_uri = _hero_data_uri()
    if data_uri:
        inner = f'<img class="hero-photo" src="{data_uri}" alt="达妮娅">'
    else:
        inner = '<div class="hero-photo hero-photo-empty"><span>达妮娅</span></div>'
    return f'''
        <div class="hero">
          {inner}
          <div class="hero-frame"></div>
          <div class="hero-caption">
            <span class="hero-name">达妮娅</span>
            <span class="hero-sub">今日老婆 · 看板娘</span>
          </div>
        </div>
    '''


def _build_empty_state() -> str:
    return '''
        <div class="empty-state">
          <div class="empty-icon">🫧</div>
          <div class="empty-title">还没有可统计的今日老婆记录</div>
          <div class="empty-sub">先去抽几次「今日老婆」吧，达妮娅会把榜单记下来的～</div>
        </div>
    '''


def _build_stat_chip(label: str, value: str) -> str:
    return (
        '<div class="stat-chip">'
        f'<span class="stat-value">{html.escape(value)}</span>'
        f'<span class="stat-label">{html.escape(label)}</span>'
        '</div>'
    )


def _build_rank_html(
    day_count: int,
    total_count: int,
    items: list[tuple[int, int, str]],
    source_label: str,
    note: str,
) -> str:
    avatar_lookup = _build_avatar_lookup()
    podium_items = items[:RANK_PODIUM_SIZE]
    rest_items = items[RANK_PODIUM_SIZE:RANK_DISPLAY_LIMIT]
    truncated_count = max(0, len(items) - RANK_DISPLAY_LIMIT)
    max_count = items[0][0] if items else 0

    if not items:
        podium_html = ''
        list_html = _build_empty_state()
    else:
        podium_html = ''.join(
            _build_podium_slot(rank, count, updated_at, name, avatar_lookup, max_count)
            for rank, (count, updated_at, name) in enumerate(podium_items, 1)
        )
        rows = ''.join(
            _build_list_row(rank, count, updated_at, name, avatar_lookup, max_count)
            for rank, (count, updated_at, name) in enumerate(rest_items, RANK_PODIUM_SIZE + 1)
        )
        tail_note = (
            f'<div class="tail-note">仅展示前 {RANK_DISPLAY_LIMIT} 名，还有 {truncated_count} 位未上榜</div>'
            if truncated_count > 0 else ''
        )
        list_html = (
            f'<div class="list-section">{rows}</div>{tail_note}'
            if rows else '<div class="list-empty-hint">已展示全部上榜角色</div>'
        )

    podium_block = f'<div class="podium">{podium_html}</div>' if podium_html else ''
    hero_html = _build_hero_html()

    safe_note = html.escape(note) if note else ''
    note_html = f'<div class="note-banner">{safe_note}</div>' if safe_note else ''
    stat_chips = (
        _build_stat_chip('统计天数', f'{day_count}')
        + _build_stat_chip('累计被娶', f'{total_count}')
        + _build_stat_chip('数据来源', source_label)
    )
    sync_time = time.strftime('%Y-%m-%d %H:%M', time.localtime())

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    width: {RANK_RENDER_WIDTH}px;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    color: #1d2c4d;
  }}
  body {{
    position: relative;
    padding: 34px;
    background: linear-gradient(160deg, #eaf3fd 0%, #d8e8fa 46%, #c6dcf6 100%);
    overflow: hidden;
  }}
  /* 柔光球：纯装饰，若渲染引擎不支持 radial-gradient 则自然不显示，不影响底色 */
  .glow-a, .glow-b {{ position: absolute; pointer-events: none; border-radius: 999px; }}
  .glow-a {{ top: -120px; right: -80px; width: 360px; height: 360px;
    background: radial-gradient(circle, rgba(150, 199, 240, 0.55), transparent 70%); }}
  .glow-b {{ bottom: -160px; left: 30%; width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(120, 170, 224, 0.40), transparent 70%); }}
  .card {{
    position: relative;
    border-radius: 30px;
    padding: 32px 34px 28px;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.9);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.9),
      0 24px 60px rgba(70, 110, 170, 0.20);
    overflow: hidden;
  }}

  /* —— 顶部：标题 + 统计 —— */
  .header {{ display: flex; align-items: flex-start; gap: 18px; }}
  .logo-badge {{
    flex: none; width: 64px; height: 64px; border-radius: 20px;
    display: flex; align-items: center; justify-content: center; font-size: 32px;
    background: linear-gradient(135deg, #7fb6ec, #5b93d8);
    box-shadow: 0 10px 22px rgba(91, 147, 216, 0.40);
    color: #fff;
  }}
  .title-block {{ flex: 1; min-width: 0; padding-top: 2px; }}
  .title-row {{ display: flex; align-items: baseline; gap: 11px; }}
  h1 {{ font-size: 28px; font-weight: 800; letter-spacing: 1px; color: #16294b; }}
  .title-badge {{
    font-size: 11.5px; padding: 3px 10px; border-radius: 999px;
    background: rgba(91, 147, 216, 0.14); border: 1px solid rgba(91, 147, 216, 0.34);
    color: #3f72b8; font-weight: 700; letter-spacing: 1px;
  }}
  .subtitle {{ margin-top: 7px; color: #5a6e92; font-size: 13.5px; line-height: 1.5; }}
  .stat-row {{ flex: none; display: flex; gap: 9px; }}
  .stat-chip {{
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-width: 76px; padding: 9px 12px; border-radius: 15px;
    background: rgba(255, 255, 255, 0.74);
    border: 1px solid rgba(120, 165, 220, 0.30);
    box-shadow: 0 6px 16px rgba(80, 130, 190, 0.10);
  }}
  .stat-value {{ font-size: 18px; font-weight: 800; color: #2a4a7e; }}
  .stat-label {{ margin-top: 3px; font-size: 11px; color: #6f82a4; }}
  .note-banner {{
    margin-top: 15px; padding: 10px 15px; border-radius: 13px; font-size: 12.5px;
    background: rgba(122, 182, 236, 0.12); border: 1px solid rgba(122, 182, 236, 0.34);
    color: #335f96;
  }}

  /* —— 中部：领奖台 + 看板娘 —— */
  .stage {{ display: flex; align-items: stretch; gap: 22px; margin-top: 22px; }}
  .stage-left {{ flex: 1; min-width: 0; display: flex; flex-direction: column; }}
  .stage-title {{
    display: flex; align-items: center; gap: 9px; margin-bottom: 16px;
    font-size: 15px; font-weight: 800; color: #20396a;
  }}
  .stage-title::before {{ content: ""; width: 4px; height: 16px; border-radius: 3px; background: linear-gradient(180deg, #7fb6ec, #4f8ad4); }}
  .stage-title .tip {{ font-size: 12px; font-weight: 500; color: #8093b4; }}

  .podium {{ display: flex; align-items: flex-end; justify-content: center; gap: 16px; flex: 1; }}
  .podium-slot {{
    flex: 1; max-width: 168px; display: flex; flex-direction: column; align-items: center;
    padding: 16px 12px 0; border-radius: 20px;
    background: rgba(255, 255, 255, 0.66);
    border: 1px solid rgba(150, 190, 235, 0.40);
    box-shadow: 0 12px 26px rgba(80, 130, 190, 0.12);
  }}
  .podium-slot.rank-1 {{ order: 2; transform: translateY(-14px); border-color: rgba(233, 196, 95, 0.55); box-shadow: 0 16px 32px rgba(214, 169, 58, 0.20); }}
  .podium-slot.rank-2 {{ order: 1; }}
  .podium-slot.rank-3 {{ order: 3; }}
  .podium-medal {{ font-size: 26px; font-weight: 800; color: var(--accent); line-height: 1; margin-bottom: 10px; }}
  .avatar-ring {{
    border-radius: 999px; padding: 4px; margin-bottom: 11px;
    background: linear-gradient(135deg, var(--ring), rgba(255, 255, 255, 0.85));
    box-shadow: 0 0 0 4px var(--ring-soft);
  }}
  .avatar {{ display: block; }}
  .avatar-img {{ border-radius: 999px; overflow: hidden; border: 3px solid #fff; }}
  .avatar-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .avatar-fallback {{
    border-radius: 999px; border: 3px solid #fff;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800;
  }}
  .podium-avatar.avatar-fallback {{ font-size: 30px; }}
  .podium-name {{
    font-size: 17px; font-weight: 800; color: #18294b; max-width: 100%;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  .podium-count {{ margin-top: 3px; font-size: 12.5px; color: #5a6e92; }}
  .podium-count b {{ color: #e1742c; font-size: 16px; }}
  .podium-date {{ margin-top: 2px; font-size: 11px; color: #8d9cb8; }}
  .podium-base {{
    margin-top: 12px; width: 100%; border-radius: 12px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.0), var(--accent));
    color: #fff;
  }}
  .podium-tag {{ font-size: 12px; font-weight: 800; letter-spacing: 1.5px; }}
  .podium-share {{ margin-top: 1px; font-size: 10px; opacity: 0.92; }}

  /* 看板娘立绘 */
  .hero {{ position: relative; flex: none; width: 268px; border-radius: 22px; overflow: hidden; box-shadow: 0 16px 36px rgba(70, 110, 170, 0.26); }}
  .hero-photo {{
    display: block; width: 100%; height: 100%;
    object-fit: cover; object-position: center 12%;
  }}
  .hero-photo-empty {{
    display: flex; align-items: center; justify-content: center; min-height: 360px;
    background: linear-gradient(150deg, #bcd7f4, #8bb6e6);
    color: #fff; font-size: 30px; font-weight: 800; letter-spacing: 4px;
  }}
  .hero-frame {{ position: absolute; inset: 0; border: 1px solid rgba(255, 255, 255, 0.55); border-radius: 22px; box-shadow: inset 0 0 0 4px rgba(255, 255, 255, 0.18); }}
  .hero-caption {{
    position: absolute; left: 0; right: 0; bottom: 0; padding: 30px 18px 16px;
    display: flex; flex-direction: column; gap: 2px;
    background: linear-gradient(0deg, rgba(20, 40, 78, 0.74), transparent);
  }}
  .hero-name {{ font-size: 19px; font-weight: 800; color: #fff; letter-spacing: 1px; }}
  .hero-sub {{ font-size: 11.5px; color: rgba(255, 255, 255, 0.86); }}

  /* —— 底部：列表区 —— */
  .list-wrap {{ margin-top: 26px; }}
  .list-section {{ display: flex; flex-wrap: wrap; gap: 11px 16px; }}
  .list-row {{
    width: 404px;
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; border-radius: 15px;
    background: rgba(255, 255, 255, 0.70);
    border: 1px solid rgba(150, 190, 235, 0.34);
    box-shadow: 0 6px 16px rgba(80, 130, 190, 0.08);
  }}
  .rank-num {{
    flex: none; width: 26px; height: 26px; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 800; color: #3f72b8;
    background: rgba(122, 182, 236, 0.16); border: 1px solid rgba(122, 182, 236, 0.32);
  }}
  .row-avatar.avatar-img, .row-avatar.avatar-fallback {{ border-width: 2px; }}
  .row-avatar.avatar-fallback {{ font-size: 18px; }}
  .row-body {{ flex: 1; min-width: 0; }}
  .row-head {{ display: flex; align-items: baseline; gap: 8px; }}
  .row-name {{
    font-size: 14.5px; font-weight: 700; color: #1c2c4e;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px;
  }}
  .row-date {{ font-size: 10.5px; color: #94a3bf; flex: none; }}
  .row-count {{ margin-left: auto; flex: none; font-size: 12.5px; color: #e1742c; font-weight: 800; }}
  .bar-track {{ margin-top: 7px; height: 6px; border-radius: 999px; background: rgba(122, 160, 210, 0.18); overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, #7fb6ec, #4f8ad4); }}

  .tail-note {{ margin-top: 14px; text-align: center; font-size: 12px; color: #7f90b0; }}
  .list-empty-hint {{ margin-top: 6px; text-align: center; font-size: 12px; color: #94a3bf; }}

  .empty-state {{
    padding: 46px 20px; text-align: center; border-radius: 20px;
    background: rgba(255, 255, 255, 0.62); border: 1px dashed rgba(122, 165, 220, 0.5);
  }}
  .empty-icon {{ font-size: 36px; margin-bottom: 10px; }}
  .empty-title {{ font-size: 16px; font-weight: 800; color: #20396a; }}
  .empty-sub {{ margin-top: 8px; font-size: 13px; color: #5a6e92; }}

  /* —— 页脚 —— */
  .footer {{
    margin-top: 26px; padding-top: 15px;
    border-top: 1px solid rgba(122, 165, 220, 0.28);
    display: flex; align-items: center; justify-content: center; gap: 8px;
    font-size: 12px; color: #7f90b0;
  }}
  .footer .brand {{ color: #3f72b8; font-weight: 800; }}
  .footer .dot {{ color: rgba(120, 150, 195, 0.5); }}
</style>
</head>
<body>
  <div class="glow-a"></div>
  <div class="glow-b"></div>
  <div class="card">
    <div class="header">
      <div class="logo-badge">👰</div>
      <div class="title-block">
        <div class="title-row">
          <h1>今日老婆总排行</h1>
          <span class="title-badge">RANKING</span>
        </div>
        <div class="subtitle">按累计被娶次数从高到低排列，仅统计鸣潮角色记录</div>
      </div>
      <div class="stat-row">{stat_chips}</div>
    </div>
    {note_html}
    <div class="stage">
      <div class="stage-left">
        <div class="stage-title">荣耀前三<span class="tip">最受欢迎的老婆</span></div>
        {podium_block if podium_block else list_html}
      </div>
      {hero_html}
    </div>
    {f'<div class="list-wrap">{list_html}</div>' if podium_block else ''}
    <div class="footer">
      <span class="brand">TodayWaifu</span><span class="dot">·</span>
      <span>达妮娅看板</span><span class="dot">·</span>
      <span>更新于 {sync_time}</span><span class="dot">·</span>
      <span>Created by <b style="color:#3f72b8;">nnlmc</b></span>
    </div>
  </div>
</body>
</html>'''


async def build_total_wife_rank_image(
    day_count: int,
    total_count: int,
    items: list[tuple[int, int, str]],
    source_label: str = '本地',
    note: str = '',
) -> Any:
    try:
        from gsuid_core.utils.html_render import render_html_to_bytes
    except Exception as exc:
        raise RuntimeError('当前 GSCore 未提供 HTML 渲染组件，请更新 GSCore 或安装 pyrenderhtml>=0.0.5。') from exc

    html_doc = _build_rank_html(day_count, total_count, items, source_label, note)
    try:
        image = await render_html_to_bytes(
            html_doc,
            max_width=RANK_RENDER_WIDTH,
            dpi=96,
            default_font_size=14,
            font_name='sans-serif',
            image_format='png',
            lang='zh',
        )
    except Exception as exc:
        raise RuntimeError('今日老婆总排行图片渲染失败，请查看控制台日志。') from exc

    try:
        from gsuid_core.utils.image.convert import convert_img

        return await convert_img(image)
    except Exception:
        return image
