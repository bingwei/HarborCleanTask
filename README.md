
# 使用说明
- 作用：执行清理过期repo的，用于释放harbor的磁盘空间

### 清理策略
- 获取所有tag, 按照createTime排序，删除93天以前的（单个环境允许其3个月进行一次全量部署）
- master分支生成的tag, 最多保留15个(根据常用环境数量评估)
- 非master分支仅保留最新的一个, 数量保留20个


### 定时任务

```
#每天执行一次
15 3 * * *
```


# 附harbor gc步骤
**在v1.7版本测试通过**

## 步骤

1. 进入www@your_server:/data/harbor目录

```
cd /data/harbor
```

2. 停止harbor，防止在删除镜像过程中有人在上传镜像，导致镜像的图层不全

```
sudo docker-compose stop
```

3. 下面的 tag 'v2.6.2-v1.5.1' 需要换成当前使用的 registry-photon 镜像的版本号

```
# --dry-run 表示尝试进行 GC，输出 log 与正式 gc 一致，可用于提前发现问题
# sudo docker run -it --name gc --rm --volumes-from registry vmware/registry-photon:v2.6.2-v1.5.1 garbage-collect --dry-run /etc/registry/config.yml

# 正式 gc，这个才会真正的 gc 掉已经软删除的镜像
sudo docker run -it --name gc --rm --volumes-from registry vmware/registry-photon:v2.6.2-v1.5.1 garbage-collect /etc/registry/config.yml

```

4. 启动harbor

```
sudo docker-compose start
```
