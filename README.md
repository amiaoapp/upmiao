# 粉丝数统计工具

这是一个基于 Flask 的粉丝数统计工具，支持多平台（如 B 站、抖音、小红书等）的粉丝数据抓取和展示。

## 快速部署指南

### 前提条件

- 一台运行 Linux 的服务器（如 Ubuntu、CentOS 等）
- Python 3.10 或更高版本
- pip（Python 包管理器）
- git

### 部署步骤

1. **克隆仓库**

   在服务器上执行以下命令，将项目代码克隆到本地：

   ```bash
   git clone https://github.com/amiaoapp/upmiao.git
   cd upmiao
   ```

2. **创建虚拟环境**

   使用 Python 的 venv 模块创建虚拟环境，避免依赖冲突：

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **安装依赖**

   在虚拟环境中安装项目所需的依赖包：

   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量（可选）**

   如需配置环境变量（如 API 密钥等），请创建 `.env` 文件并添加相关配置。

5. **启动应用**

   在虚拟环境中启动 Flask 应用：

   ```bash
   python app.py
   ```

   默认情况下，应用将在 `http://localhost:5000` 运行。

6. **使用 Nginx 和 Gunicorn 部署（推荐）**

   为生产环境部署，建议使用 Nginx 作为反向代理，Gunicorn 作为 WSGI 服务器。

   - 安装 Gunicorn：

     ```bash
     pip install gunicorn
     ```

   - 启动 Gunicorn：

     ```bash
     gunicorn -w 4 -b 127.0.0.1:8000 app:app
     ```

   - 配置 Nginx：

     在 Nginx 配置文件中添加以下内容：

     ```nginx
     server {
         listen 80;
         server_name your_domain.com;

         location / {
             proxy_pass http://127.0.0.1:8000;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
         }
     }
     ```

     替换 `your_domain.com` 为你的域名，重启 Nginx：

     ```bash
     sudo systemctl restart nginx
     ```

### 访问应用

完成部署后，通过浏览器访问 `http://your_domain.com` 即可使用粉丝数统计工具。

## 贡献

欢迎提交 Issue 和 Pull Request，共同完善项目！

## 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](LICENSE) 文件。
