#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: bing.wei
# Email: vveibing@163.com
from __future__ import print_function, division

import sys

# import here

reload(sys)
sys.setdefaultencoding('utf-8')

import requests
import datetime
import re

class RequestClient(object):

    def __init__(self, login_url, username, password):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.session = requests.Session()
        self.login()

    def login(self):
        self.session.post(self.login_url, params={"principal": self.username, "password": self.password})


class ClearHarbor(object):

    def __init__(self, harbor_domain, password, schema="https",
                 username="admin"):
        self.schema = schema
        self.harbor_domain = harbor_domain
        self.harbor_url = self.schema + "://" + self.harbor_domain
        self.login_url = self.harbor_url + "/c/login"
        self.api_url = self.harbor_url + "/api"
        self.pro_url = self.api_url + "/projects"
        self.repos_url = self.api_url + "/repositories"
        self.username = username
        self.password = password
        self.client = RequestClient(self.login_url, self.username, self.password)
        # master分支得到的tag最大保留数量
        self.image_master_tags_limit = 15
        # 非master分支仅保留最新的一个tag, 最多非master分支允许保留的tag数量
        self.image_branch_limit = 15
        # 最长保留3个月，93天
        self.dates_keep_limit = 93
        self.the_date = self.__specific_date()

    def __specific_date(self):
        """
        返回保留的截止时间点
        :return:
        """
        today = datetime.datetime.now()
        # hours=-8 用于修正时间到时区为0，确保和harbor中的create_time的时区一致
        offset = datetime.timedelta(days=-1 * self.dates_keep_limit, hours=-8)
        re_date = (today + offset).strftime("%Y-%m-%d %H:%M:%S")
        return re_date

    def fetch_all_testing_repos_name(self, pro_id=3):
        """
        处理某个project的数据
        :param pro_id:
        :return:
        """
        all_repos_name = []
        repos_resp = self.client.session.get(self.repos_url, params={"project_id": pro_id})

        for repo in repos_resp.json():
            all_repos_name.append(repo['name'])
        return all_repos_name

    def clean_repo_name_tags(self, repo_name):
        """
        检查每一个repo是否需要进行清理，收集tag然后开始处理
        删除策略
            - 获取所有tag, 按照createTime排序，删除93天以前的（单个环境允许其3个月进行一次全量部署）
            - master分支生成的tag, 最多保留 image_master_tags_limit 个(根据常用环境数量评估)
            - 非master分支仅保留最新的一个, 总分支数量保留 image_branch_limit 个

        :param repo_name:
        :return:
        """
        del_tags = []
        branch_tags_map = dict()
        branchs = []

        tag_url = self.repos_url + "/" + repo_name + "/tags"
        # TODO
        tags = self.client.session.get(tag_url).json()
        # tags_sort时间由最新到最老
        tags_sort = sorted(tags, key=lambda a: a["created"])
        tags_sort.reverse()

        for i_tag in tags_sort:
            if self.__is_in_limit_date(i_tag["created"]):
                tag_name = i_tag["name"]
                branch_name = self.__retrieve_branch(tag_name)
                if branch_name not in branchs:
                    branchs.append(branch_name)
                    branch_tags_map.setdefault(branch_name, [])
                branch_tags_map.get(branch_name).append(tag_name)
            else:
                del_tags.append(i_tag["name"])

        # master最多保留 image_master_tags_limit 个分支
        if "master" in branch_tags_map:
            master_tags = branch_tags_map.pop("master")
            del_tags.extend(master_tags[self.image_master_tags_limit:])

        # 非master分支，最多保留 image_branch_limit 个分支
        if "master" in branchs:
            branchs.remove("master")
        for br in branchs[self.image_branch_limit:]:
            del_tags.extend(branch_tags_map.get(br))

        # 非master分支，仅保留最新的一个tag
        for _, tag_name_list in branch_tags_map.items():
            del_tags.extend(tag_name_list[1:])

        self.__clean_tags(tag_url, del_tags)
        print("=========== >> deleted repo size: {:3} << ===========\n".format(len(del_tags)))

    def __retrieve_branch(self, tag_name):
        """
        tag格式: branchName_YYYYMMDD-HHmmSS
        兼容处理之前并未遵循该格式的tag
        """
        ret = re.findall(r"(\S+)_[0-9]{8}-[0-9]{6}$", tag_name)
        if ret:
            return ret[0]
        else:
            return tag_name

    def __is_in_limit_date(self, _str_date):
        """
        判断是否仍可保留
        :return:
        """
        if _str_date > self.the_date:
            return True
        else:
            return False

    def __clean_tags(self, tag_url, del_tags=[]):
        for idx, tag in enumerate(del_tags):
            del_repo_tag_url = tag_url + "/" + tag
            print("%03d. %s" % (idx+1, del_repo_tag_url))
            self.client.session.delete(del_repo_tag_url)


if __name__ == "__main__":

    harbor_domain = "YOUR_HARBOR_DOMAIN"
    password = "HARBOR_ADMIN_PASSWORD"
    harbor_client = ClearHarbor(harbor_domain, password)

    for i, repo_name in enumerate(harbor_client.fetch_all_testing_repos_name()):
        print("%03d. prepare to clean repo: %s" % (i, repo_name))
        print("-" * 50)
        harbor_client.clean_repo_name_tags(repo_name)

    print("end")
