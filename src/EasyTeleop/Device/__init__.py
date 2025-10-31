import os
import importlib
from typing import Dict, Type, Any
from .BaseDevice import BaseDevice

__all__ = [
    'BaseDevice',
    'get_device_classes',
    'get_device_types'
]

def get_device_classes() -> Dict[str, Dict[str, Type]]:
    """
    动态获取所有设备类
    :return: 设备类字典，格式为 {category: {type: class}}
    """
    device_classes = {}
    
    # 获取当前目录
    current_dir = os.path.dirname(__file__)
    
    # 遍历设备类别目录
    for category in os.listdir(current_dir):
        category_path = os.path.join(current_dir, category)
        if os.path.isdir(category_path) and not category.startswith('__'):
            device_classes[category] = {}
            
            # 遍历类别目录下的所有Python文件
            for filename in os.listdir(category_path):
                if filename.endswith('.py') and filename != '__init__.py':
                    # 获取模块名（去掉.py后缀）
                    module_name = filename[:-3]
                    
                    try:
                        # 动态导入模块 - 使用相对导入路径
                        module = importlib.import_module(f'.{category}.{module_name}', package='EasyTeleop.Device')
                        
                        # 尝试获取与模块名相同的类
                        if hasattr(module, module_name):
                            device_class = getattr(module, module_name)
                            
                            # 检查是否为类且继承自BaseDevice
                            if (isinstance(device_class, type) and 
                                issubclass(device_class, BaseDevice)):
                                
                                # 排除Base开头的类和Base+category名字的类
                                if (not device_class.__name__.startswith('Base') and 
                                    device_class.__name__ != f"Base{category}"):
                                    
                                    # 使用类名作为type
                                    device_classes[category][device_class.__name__] = device_class
                                
                    except Exception as e:
                        print(f"导入模块 EasyTeleop.Device.{category}.{module_name} 时出错: {e}")
    
    return device_classes


def get_device_types() -> Dict[str, Dict[str, Any]]:
    """
    动态获取所有设备类型及其配置信息
    :return: 设备类型配置字典，格式为 {category: {type: need_config}}
    """
    device_types = {}
    
    # 获取当前目录
    current_dir = os.path.dirname(__file__)
    
    # 遍历设备类别目录
    for category in os.listdir(current_dir):
        category_path = os.path.join(current_dir, category)
        if os.path.isdir(category_path) and not category.startswith('__'):
            device_types[category] = {}
            
            # 遍历类别目录下的所有Python文件
            for filename in os.listdir(category_path):
                if filename.endswith('.py') and filename != '__init__.py':
                    # 获取模块名（去掉.py后缀）
                    module_name = filename[:-3]
                    
                    try:
                        # 动态导入模块 - 使用相对导入路径
                        module = importlib.import_module(f'.{category}.{module_name}', package='EasyTeleop.Device')
                        
                        # 尝试获取与模块名相同的类
                        if hasattr(module, module_name):
                            device_class = getattr(module, module_name)
                            
                            # 检查是否为类且继承自BaseDevice
                            if (isinstance(device_class, type) and 
                                issubclass(device_class, BaseDevice)):
                                
                                # 排除Base开头的类和Base+category名字的类，并检查是否有need_config属性
                                if (not device_class.__name__.startswith('Base') and 
                                    device_class.__name__ != f"Base{category}" and
                                    hasattr(device_class, 'need_config')):
                                    
                                    # 使用类名作为type
                                    device_types[category][device_class.__name__] = device_class.get_type_info()
                    except Exception as e:
                        print(f"导入模块 EasyTeleop.Device.{category}.{module_name} 时出错: {e}")
    
    return device_types