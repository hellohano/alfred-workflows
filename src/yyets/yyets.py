#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import warnings
import time
import json
import base64
from pprint import pprint

import alfred
alfred.setDefaultEncodingUTF8()
import bs4

def parseWebPage(url, **kwargs):
    try:
        res = alfred.request.get(url, **kwargs)
        content = res.getContent()
        # 禁止显示BeautifulSoup警告
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return bs4.BeautifulSoup(content)
    except Exception, e:
        raise e

# 获取最新更新
def fetchRecentItems(channel):
    # channel: movie tv documentary openclass topic
    search_channel = ''
    # 如果查找的类别不为空的话，获取其完整的正确名称
    if channel:
        for valid_chl in ['movie', 'tv', 'documentary', 'openclass', 'topic']:
            if valid_chl.startswith(channel):
                search_channel = valid_chl
        if not search_channel:
            return []
    cache_name = 'recent-{}-items'.format(search_channel)
    cache = alfred.cache.get(cache_name)
    if cache:
        return cache
    items = []
    soup = parseWebPage(
        'http://www.yyets.com/resourcelist',
        data = {
            'channel'   : search_channel,
            'sort'      : 'update'
        }
    )
    # pprint(soup.select('ul.boxPadd li'))
    for single in soup.select('ul.boxPadd li'):
        item = {}
        try:
            # 图片 页面地址
            item['page'] = single.select('div.f_l_img')[0].a['href']
            item['img'] = single.select('div.f_l_img')[0].img['src']
            top_str = single.select('div.f_l_img')[0].get_text()

            info = single.select('div.f_r_info dl')[0]
            # 标题
            item['title'] = info.dt.get_text(' ', strip=True)
            map(lambda t: t.font.clear(),info.dd.select('span'))
            # 说明 人气
            item['info'] = '说明: {} 人气: {}'.format(   
                info.dd.select('span')[0].get_text('', strip=True),
                info.dd.select('span')[2].get_text('', strip=True)
            )
            items.append(item)
        except Exception, e:
            # 忽略错误
            continue
    if not items:
        return []
    # 缓存5分钟
    alfred.cache.set(cache_name, items, 60*5)
    return items


# 获取今日更新（包括昨日与前天）
def fetchTodayItems():
    cache = alfred.cache.get('today-items')
    if cache:
        return cache
    items = []
    soup = parseWebPage('http://www.yyets.com/html/today.html')
    for single in soup.select('div.day_data tr.list'):
        item = {}
        info = single.select('td')
        # 类别
        item['type'] = info[0].get_text()
        # 格式
        item['format'] = info[1].get_text()
        # 文件名 及 页面链接
        _tmp = info[2].find('a')
        if not _tmp:
            continue
        item['filename'] = _tmp.get_text()
        item['page'] = _tmp['href']
        # 下载链接 只关心电驴 和 磁力链
        item['emule'] = ''
        item['magnet'] = ''
        if info[3].select('a.c'):
            item['magnet'] = info[3].select('a.c')[0]['href']
        if info[3].select('a.l'):
            item['emule'] = info[3].select('a.l')[0]['href']
        # 容量
        item['size'] = info[4].get_text()
        # 更新时间
        item['date'] = '{} {}'.format(single['day'], info[5].get_text())
        items.append(item)
    if not items:
        return []
    # 缓存5分钟
    alfred.cache.set('today-items', items, 60*5) 
    return items

# 获取24小时热门榜
def fetchTopItems():
    cache = alfred.cache.get('top-items')
    if cache:
        return cache
    items = []
    soup = parseWebPage('http://www.yyets.com/resourcelist')
    for single in soup.select('ul.top_list2 li'):
        item = {}
        # 照片 页面链接
        img_ele = single.select('div.f_l_img')
        if img_ele:
            item['page'] = img_ele[0].a['href']
            item['img'] = img_ele[0].a.img['src']
        info = single.select('div.f_r_info div')
        if info:
            # 标题
            item['title'] = info[0].get_text().strip('《》')
            item['info'] = '{} {} {}'.format(info[1].get_text(), info[2].get_text(), info[3].get_text())
        # pprint(item)
        items.append(item)
    if not items:
        return []
    # 缓存5分钟
    alfred.cache.set('top-items', items, 60*5)
    return items

# 获取搜索结果
def fetchSearchResult(word):
    if not word:
        return []
    items = []
    soup = parseWebPage(
        'http://www.yyets.com/search/index',
        data = {
            'keyword'   : '{}'.format(word),
            'type'      : 'resource',
            'order'     : 'uptime'
        }
    )
    for single in soup.select('ul.allsearch li'):
        item = {}
        try:
            # 标题 页面地址
            item['title'] = single.select('div.all_search_li2')[0].get_text()
            item['page'] = single.select('div.all_search_li2')[0].a['href']
            # print(single.select('div.all_search_li3')[0].get_text())
            # 信息
            pub_time = time.localtime(float(single.select('span.time')[0].get_text().strip()))
            update_time = time.localtime(float(single.select('span.time')[1].get_text().strip()))
            item['info'] = '类型:{} 发布时间:{} 更新时间:{} {}'.format(
                single.select('div.all_search_li1')[0].get_text().strip(),
                time.strftime('%Y-%m-%d %H:%I', pub_time),
                time.strftime('%Y-%m-%d %H:%I', update_time),
                single.select('div.all_search_li3')[0].get_text().strip()
            )
        except Exception, e:
            # raise e
            # 忽略错误
            continue
        items.append(item)
    return items

# 获取最新更新
def recent():
    feedback = alfred.Feedback()
    try:
        for item in fetchRecentItems(alfred.argv(2)):
            feedback.addItem(
                title       = item['title'],
                subtitle    = item['info'],
                icon        = alfred.storage.getLocalIfExists(item['img'], True),
                arg         = item['page']
            )
    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

# 最近今日更新
def today():
    feedback = alfred.Feedback()
    try:
        filter_str = alfred.argv(2)
        if filter_str:
            filter_str = filter_str.upper()
        feedback = alfred.Feedback()
        for item in fetchTodayItems():
            if filter_str and filter_str not in item['format']:
                continue
            item['has_emule'] = '有' if item['emule'] else '无'
            item['has_magnet'] = '有' if item['magnet'] else '无'
            subtitle = '类别: {type}  格式: {format}  容量: {size}  日期: {date}  电驴: {has_emule}  磁力链: {has_magnet}'.format(**item)
            feedback.addItem(
                title       = item['filename'],
                subtitle    = subtitle,
                arg         = base64.b64encode('{page},{emule},{magnet}'.format(**item))
            )
    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

# 24小时最热资源
def top():
    feedback = alfred.Feedback()
    try:
        for item in fetchTopItems():
            feedback.addItem(
                title       = item['title'],
                subtitle    = item['info'],
                icon        = alfred.storage.getLocalIfExists(item['img'], True),
                arg         = item['page']
            )

    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

def search():
    feedback = alfred.Feedback()
    try:
        for item in fetchSearchResult(alfred.argv(2)):
            feedback.addItem(
                title       = item['title'],
                subtitle    = item['info'],
                arg         = item['page']
            )
    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

def main():
    cmds = {
        'recent'    : lambda: recent(),
        'today'     : lambda: today(),
        'top'       : lambda: top(),
        'search'    : lambda: search()
    }
    subcmd = alfred.argv(1)
    if subcmd and subcmd.lower() in cmds.keys():
        cmds[subcmd.lower()]()

if __name__ == '__main__':
    main()