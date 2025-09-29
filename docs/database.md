# 数据库说明

EasyTeleop 系统使用 SQLite 数据库来存储设备和遥操作组的配置信息。

## 数据库结构

### nodes 表

存储节点信息。

| 字段名 | 类型 | 描述 |
| --- | --- | --- |
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 节点ID |
| uuid | VARCHAR(36) UNIQUE NOT NULL | 节点UUID |
| status | BOOLEAN DEFAULT 1 | 节点状态 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 更新时间 |

### devices 表

存储设备信息。

| 字段名 | 类型 | 描述 |
| --- | --- | --- |
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 设备ID |
| node_id | INTEGER NOT NULL | 节点ID |
| name | VARCHAR(20) NOT NULL | 设备名称 |
| description | TEXT NOT NULL | 设备描述 |
| category | VARCHAR(20) NOT NULL | 设备类别（robot, vr, camera） |
| type | VARCHAR(20) NOT NULL | 设备类型（RealMan, Quest, RealSense等） |
| config | TEXT NOT NULL | 设备配置（JSON格式） |
| status | INTEGER DEFAULT 0 | 设备状态（0=未连接, 1=已连接, 2=断开连接） |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| FOREIGN KEY (node_id) | REFERENCES nodes (id) | 外键约束 |

### teleop_groups 表

存储遥操作组信息。

| 字段名 | 类型 | 描述 |
| --- | --- | --- |
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 遥操作组ID |
| node_id | INTEGER NOT NULL | 节点ID |
| name | VARCHAR(100) NOT NULL | 遥操作组名称 |
| description | TEXT | 遥操作组描述 |
| type | VARCHAR(50) NOT NULL | 遥操作组类型 |
| config | TEXT NOT NULL | 遥操作组配置（JSON格式，包含设备ID列表） |
| status | BOOLEAN DEFAULT 0 | 遥操作组状态 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| FOREIGN KEY (node_id) | REFERENCES nodes (id) | 外键约束 |

## 数据库初始化

数据库在系统启动时自动初始化，创建所需的表结构。

```python
def init_device_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建 nodes 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid VARCHAR(36) UNIQUE NOT NULL,
            status BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建 devices 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            name VARCHAR(20) NOT NULL,
            describe TEXT NOT NULL,
            category VARCHAR(20) NOT NULL,
            type VARCHAR(20) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES nodes (id)
        )
    ''')
    
    # 创建 teleop_groups 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teleop_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            describe TEXT,
            type VARCHAR(50) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status BOOLEAN DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES nodes (id)
        )
    ''')
    
    conn.commit()
    conn.close()
```

## 数据访问

系统通过以下函数访问数据库：

- `get_db_conn()`：获取数据库连接
- `init_device_tables()`：初始化数据库表
- 各种 API 接口函数直接访问数据库获取和更新数据