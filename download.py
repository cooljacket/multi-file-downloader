# coding: utf-8
# 参考：https://blog.csdn.net/qq_35203425/article/details/80987880
import requests
import os
import multiprocessing
import time

# 屏蔽warning信息
requests.packages.urllib3.disable_warnings()


def get_remote_file_size(url):
    '''获取远程文件的大小'''
    req = requests.get(url, stream=True, verify=False)
    total_size = int(req.headers['Content-Length'])
    return total_size


def download_file(url, file_path):
    total_size = get_remote_file_size(url)
    _, filename = os.path.split(file_path)

    # 断点续传：先看看本地文件下载了多少
    if os.path.exists(file_path):
        now_size = os.path.getsize(file_path)  # 本地已经下载的文件大小
    else:
        now_size = 0
    if now_size >= total_size:
        return

    print('Start to download {file_path}, total={total}, now={now}'.format(
        file_path=file_path, total=total_size, now=now_size))

    start_time = time.time()

    # 核心部分：设置http的header，要求远程服务器从指定位置开始返回文件内容
    headers = {'Range': 'bytes=%d-' % now_size}  
    req = requests.get(url, stream=True, verify=False, headers=headers)

    # "ab"表示追加形式写入文件
    last_done_rate = 0
    last_time = time.time()
    last_size = now_size
    with open(file_path, "ab") as f:
        for chunk in req.iter_content(chunk_size=4096):
            if chunk:
                now_size += len(chunk)
                f.write(chunk)
                # f.flush()   # 这里其实没必要每次f.write都flush

                # 显示下载的进度、速度
                done_rate = int(1000 * now_size / total_size)
                if done_rate > last_done_rate:
                    speed = int((now_size-last_size) / 1024 / (time.time()-last_time))

                    last_done_rate = done_rate
                    last_time = time.time()
                    last_size = now_size

                    cost_min = int((time.time()-start_time+59) / 60)
                    print("{filename}:\t{rate:.1f}%\t| cost_time={cost} min | speed={speed} k/s".format(
                        filename=filename, rate=done_rate/10, cost=cost_min, speed=speed))


def concurrent_download(data_dir, to_download_list, pool_size):
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    pool = multiprocessing.Pool(processes=pool_size)
    for url, filename in to_download_list:
        file_path = os.path.join(data_dir, filename)
        pool.apply_async(download_file, args=(url, file_path))
    pool.close()
    pool.join()


def main(data_dir, file_list_to_download):
    to_download_list = []
    with open(file_list_to_download) as f:
        for line in f:
            line = line.strip().split(' ')
            url = line[0]
            filename = ' '.join(line[1:])
            to_download_list.append((url, filename))
    
    MAX_POOL_SIZE = 30  # 可以自行调整最大进程池的大小，默认30
    pool_size = min(MAX_POOL_SIZE, len(to_download_list))
    concurrent_download(data_dir, to_download_list, pool_size)

if __name__ == '__main__':
    main('./download_result', 'files_to_download.txt')

