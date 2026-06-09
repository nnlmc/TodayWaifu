from __future__ import annotations

import asyncio
import base64
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from gsuid_core.bot import Bot
from gsuid_core.config import core_config
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.sv import Plugins, SV

from .daily_wife_config import DailyWifeConfig


Plugins(
    name='gs_wuwa_daily_wife',
    disable_force_prefix=True,
    allow_empty_prefix=True,
)

sv = SV('鸣潮今日老婆')
BASE_DIR = Path(__file__).parent
DEFAULT_GALLERY_API_URL = 'https://img.xlinxc.cn/api/xwuid/roles'
CACHE_TTL_SECONDS = 300
EXCLUDED_ROLE_NAMES = {
    '仇远',
    '凌阳',
    '卡卡罗',
    '布兰特',
    '忌炎',
    '渊武',
    '相里要',
    '秋水',
    '莫特斐',
    '陆·赫斯',
}
EXCLUDED_ROLE_KEYWORDS = ('漂泊者',)
CANDIDATE_CACHE: tuple[float, tuple['RoleCandidate', ...]] | None = None


@dataclass(frozen=True)
class RoleCandidate:
    name: str
    role_ids: tuple[str, ...]
    images: tuple[str, ...]


@dataclass(frozen=True)
class WifeRecord:
    name: str
    role_ids: tuple[str, ...]
    image: str

    @classmethod
    def from_role(cls, role: RoleCandidate, image: str) -> 'WifeRecord':
        return cls(role.name, role.role_ids, image)

    def to_role(self) -> RoleCandidate:
        return RoleCandidate(self.name, self.role_ids, (self.image,))


def _cfg(key: str) -> Any:
    return DailyWifeConfig.get_config(key).data


def _gallery_api_url() -> str:
    return str(_cfg('DailyWifeGalleryApiUrl') or DEFAULT_GALLERY_API_URL).strip()


def _gallery_auth_header() -> str | None:
    username = str(_cfg('DailyWifeGalleryUsername') or '').strip()
    password = str(_cfg('DailyWifeGalleryPassword') or '').strip()
    if not username or not password:
        return None
    token = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')
    return f'Basic {token}'


def _request_headers() -> dict[str, str]:
    headers = {'User-Agent': 'gs_wuwa_daily_wife/1.0'}
    auth = _gallery_auth_header()
    if auth:
        headers['Authorization'] = auth
    return headers


def _http_get(url: str, *, timeout: int = 15) -> bytes:
    request = Request(url, headers=_request_headers())
    with urlopen(request, timeout=timeout) as resp:
        return resp.read()


def _fetch_gallery_payload_sync() -> dict[str, Any]:
    api_url = _gallery_api_url()
    if not api_url:
        raise RuntimeError('未配置画廊接口地址。')
    try:
        body = _http_get(api_url, timeout=15)
    except HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError('画廊账号或密码不正确，接口返回 401。') from exc
        raise RuntimeError(f'请求画廊接口失败，HTTP {exc.code}。') from exc
    except URLError as exc:
        raise RuntimeError(f'请求画廊接口失败：{exc.reason}') from exc
    except TimeoutError as exc:
        raise RuntimeError('请求画廊接口超时。') from exc

    try:
        payload = json.loads(body.decode('utf-8'))
    except Exception as exc:
        raise RuntimeError('画廊接口返回内容不是有效 JSON。') from exc
    if not isinstance(payload, dict):
        raise RuntimeError('画廊接口返回格式不正确。')
    return payload


def _is_excluded_role(name: str) -> bool:
    return name in EXCLUDED_ROLE_NAMES or any(keyword in name for keyword in EXCLUDED_ROLE_KEYWORDS)


def _parse_role_candidates(payload: dict[str, Any]) -> tuple[RoleCandidate, ...]:
    roles_data = payload.get('roles')
    if not isinstance(roles_data, list):
        return ()

    candidates: list[RoleCandidate] = []
    for item in roles_data:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if not name or _is_excluded_role(name):
            continue

        role_ids_data = item.get('role_ids') or []
        role_ids = tuple(str(role_id) for role_id in role_ids_data if str(role_id).strip())

        images: list[str] = []
        for image_item in item.get('images') or []:
            if isinstance(image_item, dict):
                url = str(image_item.get('url') or '').strip()
            else:
                url = str(image_item or '').strip()
            if url.startswith(('http://', 'https://')):
                images.append(url)
        if images:
            candidates.append(RoleCandidate(name=name, role_ids=role_ids, images=tuple(images)))

    return tuple(sorted(candidates, key=lambda role: role.name))


async def _load_candidates() -> tuple[tuple[RoleCandidate, ...] | None, str | None]:
    global CANDIDATE_CACHE

    now = time.time()
    if CANDIDATE_CACHE and now - CANDIDATE_CACHE[0] < CACHE_TTL_SECONDS:
        return CANDIDATE_CACHE[1], None

    try:
        payload = await asyncio.to_thread(_fetch_gallery_payload_sync)
        candidates = _parse_role_candidates(payload)
    except RuntimeError as exc:
        logger.warning(f'[gs_wuwa_daily_wife] 读取画廊接口失败: {exc}')
        return None, str(exc)
    except Exception as exc:
        logger.warning(f'[gs_wuwa_daily_wife] 读取画廊接口异常: {exc}')
        return None, '读取画廊接口失败。'

    if not candidates:
        return None, '画廊接口里没有找到可用的角色立绘。'

    CANDIDATE_CACHE = (now, candidates)
    return candidates, None


def _download_image_sync(url: str) -> bytes:
    try:
        return _http_get(url, timeout=20)
    except HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError('画廊账号或密码不正确，图片返回 401。') from exc
        raise RuntimeError(f'下载图片失败，HTTP {exc.code}。') from exc
    except URLError as exc:
        raise RuntimeError(f'下载图片失败：{exc.reason}') from exc
    except TimeoutError as exc:
        raise RuntimeError('下载图片超时。') from exc


async def _download_image(url: str) -> bytes:
    return await asyncio.to_thread(_download_image_sync, url)


def _daily_rng(ev: Event, user_id: str | int | None = None) -> random.Random:
    group_key = ev.group_id or 'direct'
    target_user_id = ev.user_id if user_id is None else user_id
    seed = f'{date.today().isoformat()}:{target_user_id}:{group_key}'
    return random.Random(seed)


def _is_master(ev: Event) -> bool:
    try:
        masters = core_config.get_config('masters')
    except Exception:
        masters = []
    return str(ev.user_id) in {str(master) for master in masters}


def _event_rng(ev: Event) -> random.Random:
    if bool(_cfg('DailyWifeMasterUnlimited')) and _is_master(ev):
        return random.Random()
    return _daily_rng(ev)


def _wife_data_path() -> Path:
    return BASE_DIR / 'daily_wife_data.json'


def _today_key() -> str:
    return date.today().isoformat()


def _context_key(ev: Event) -> str:
    return f'{ev.bot_id}:{ev.group_id or "direct"}'


def _user_key(ev: Event, user_id: str | int | None = None) -> str:
    return str(ev.user_id if user_id is None else user_id)


def _load_wife_data() -> dict[str, Any]:
    path = _wife_data_path()
    if not path.is_file():
        return {'days': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        logger.warning(f'[gs_wuwa_daily_wife] 读取数据文件失败，将使用空数据: {exc}')
        return {'days': {}}
    if not isinstance(data, dict):
        return {'days': {}}
    data.setdefault('days', {})
    return data


def _save_wife_data(data: dict[str, Any]) -> None:
    _wife_data_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _get_today_context(data: dict[str, Any], ev: Event) -> dict[str, Any]:
    day = data.setdefault('days', {}).setdefault(_today_key(), {})
    context = day.setdefault(_context_key(ev), {})
    context.setdefault('wives', {})
    context.setdefault('rob_attempts', {})
    return context


def _record_to_dict(record: WifeRecord) -> dict[str, Any]:
    return {'name': record.name, 'role_ids': list(record.role_ids), 'image': record.image}


def _record_from_dict(data: dict[str, Any]) -> WifeRecord | None:
    try:
        record = WifeRecord(
            name=str(data['name']),
            role_ids=tuple(str(item) for item in data.get('role_ids', ())),
            image=str(data['image']),
        )
    except Exception:
        return None
    if not record.name or not record.image.startswith(('http://', 'https://')):
        return None
    return record


def _get_event_target_user_id(ev: Event) -> str | None:
    at_list = getattr(ev, 'at_list', None)
    if at_list:
        value = next(iter(at_list), None)
        if value:
            return str(value)

    for attr in ('at', 'target_id', 'target_user_id'):
        value = getattr(ev, attr, None)
        if value:
            if isinstance(value, (list, tuple, set)):
                value = next(iter(value), None)
            if value:
                return str(value)

    raw_text = str(getattr(ev, 'text', '') or getattr(ev, 'raw_text', '') or '').strip()
    match = re.search(r'(?:@|qq=|qq:|QQ=|QQ:)?(\d{5,20})', raw_text)
    if match:
        return match.group(1)
    return None


def _rob_success_rate() -> float:
    try:
        value = float(_cfg('DailyWifeRobSuccessRate'))
    except (TypeError, ValueError):
        value = 0.5
    return max(0.0, min(1.0, value))


def _build_rob_success_text(role: RoleCandidate, target_user_id: str) -> str:
    return str(_cfg('DailyWifeRobSuccessTemplate') or '抢老婆成功！你把对方今天的老婆{name}抢过来了！').format(
        name=role.name,
        role_id='/'.join(role.role_ids),
        target=target_user_id,
    )


def _build_text(role: RoleCandidate) -> str:
    lines = [
        str(_cfg('DailyWifeTextTemplate') or '你今天的老婆是{name}').format(
            name=role.name,
            role_id='/'.join(role.role_ids),
        )
    ]
    if bool(_cfg('DailyWifeShowRoleId')):
        lines.append(f'角色ID：{"/".join(role.role_ids)}')
    return '\n'.join(lines)


async def _ensure_daily_wife_record(ev: Event, user_id: str | int | None = None) -> WifeRecord | None:
    data = _load_wife_data()
    context = _get_today_context(data, ev)
    key = _user_key(ev, user_id)
    current = context['wives'].get(key)
    if isinstance(current, dict):
        record = _record_from_dict(current)
        if record is not None:
            return record

    candidates, error = await _load_candidates()
    if error or not candidates:
        return None

    rng = _daily_rng(ev, key)
    role = rng.choice(candidates)
    image = rng.choice(role.images)
    record = WifeRecord.from_role(role, image)
    context['wives'][key] = _record_to_dict(record)
    _save_wife_data(data)
    return record


async def _send_role_image(
    bot: Bot,
    role: RoleCandidate,
    image_url: str,
    text: str | None = None,
    user_id: str | int | None = None,
) -> None:
    try:
        image = await _download_image(image_url)
    except RuntimeError as exc:
        logger.warning(f'[gs_wuwa_daily_wife] 下载画廊图片失败: {exc}')
        await bot.send(str(exc))
        return

    messages: list[Any] = []
    if user_id is not None and bool(_cfg('DailyWifeAtUser')):
        messages.append(MessageSegment.at(user_id))
    if text:
        messages.append(text)
    messages.append(MessageSegment.image(image))
    await bot.send(messages if len(messages) > 1 else messages[0])


async def _send_daily_wife(bot: Bot, ev: Event):
    candidates, error = await _load_candidates()
    if error or not candidates:
        return await bot.send(error or '没有找到可用角色。')

    rng = _event_rng(ev)
    if bool(_cfg('DailyWifeMasterUnlimited')) and _is_master(ev):
        role = rng.choice(candidates)
        image = rng.choice(role.images)
        record = WifeRecord.from_role(role, image)
    else:
        record = await _ensure_daily_wife_record(ev)
        if record is None:
            return await bot.send('没有找到可用角色。')
        role = record.to_role()
        image = record.image

    logger.info(
        f'[gs_wuwa_daily_wife] user={ev.user_id} group={ev.group_id or "direct"} '
        f'role={role.name} ids={role.role_ids} image={image}'
    )

    text = _build_text(role) if bool(_cfg('DailyWifeSendText')) else None
    await _send_role_image(bot, role, image, text, ev.user_id)


async def _send_rob_wife(bot: Bot, ev: Event):
    target_user_id = _get_event_target_user_id(ev)
    if not target_user_id:
        return await bot.send('要抢谁的老婆？请艾特对方或在命令后面写对方 QQ。')

    robber_id = _user_key(ev)
    if target_user_id == robber_id:
        return await bot.send('自己抢自己的老婆也太奇怪了吧！')

    target_record = await _ensure_daily_wife_record(ev, target_user_id)
    if target_record is None:
        return await bot.send('还没找到可以抢的老婆。')

    data = _load_wife_data()
    context = _get_today_context(data, ev)
    attempts = context.setdefault('rob_attempts', {})
    is_master = _is_master(ev)
    if not is_master and attempts.get(robber_id):
        return await bot.send('今天已经抢过老婆啦，明天再来吧！')

    if not is_master:
        attempts[robber_id] = True

    if random.random() >= _rob_success_rate():
        _save_wife_data(data)
        return await bot.send('抢老婆失败了，还被对方痛扁了一顿！🤣')

    context['wives'][robber_id] = _record_to_dict(target_record)
    _save_wife_data(data)

    role = target_record.to_role()
    text = _build_rob_success_text(role, target_user_id)
    if bool(_cfg('DailyWifeSendText')):
        await _send_role_image(bot, role, target_record.image, text, robber_id)
    else:
        await bot.send(text)


@sv.on_fullmatch('今日老婆', block=True)
async def daily_wife(bot: Bot, ev: Event):
    await _send_daily_wife(bot, ev)


@sv.on_prefix(('抢老婆', '抢今日老婆'), block=True)
async def rob_wife(bot: Bot, ev: Event):
    await _send_rob_wife(bot, ev)
