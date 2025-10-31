import os
import importlib
from typing import Dict, Any, Type
from .BaseTeleopGroup import BaseTeleopGroup
from .SingleArmWithTriggerTeleopGroup import SingleArmWithTriggerTeleopGroup
from .TwoArmWithTriggerTeleopGroup import TwoArmWithTriggerTeleopGroup


def get_teleop_group_types() -> Dict[str, Any]:
    """
    动态获取所有遥操组类型配置
    :return: 遥操组类型配置字典
    """
    teleop_group_types = {}
    
    # 获取当前目录
    current_dir = os.path.dirname(__file__)
    
    # 遍历当前目录下的所有Python文件
    for filename in os.listdir(current_dir):
        if (filename.endswith('.py') and 
            filename not in ('__init__.py', 'BaseTeleopGroup.py')):
            
            # 获取模块名（去掉.py后缀）
            module_name = filename[:-3]
            
            try:
                # 动态导入模块 - 使用相对导入路径
                module = importlib.import_module(f'.{module_name}', package='EasyTeleop.TeleopGroup')
                
                # 查找模块中的类（非基类且继承自BaseTeleopGroup）
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, module.BaseTeleopGroup) and 
                        attr != module.BaseTeleopGroup):
                        
                        # 获取类型名称并添加到字典中
                        type_name = attr.get_type_name()
                        teleop_group_types[type_name] = attr.get_type_info()
                        break
                        
            except Exception as e:
                print(f"导入模块 EasyTeleop.TeleopGroup.{module_name} 时出错: {e}")
    
    return teleop_group_types


def get_teleop_group_classes() -> Dict[str, Type]:
    """
    动态获取所有遥操组类型类
    :return: 遥操组类型类字典
    """
    teleop_group_classes = {}
    
    # 获取当前目录
    current_dir = os.path.dirname(__file__)
    
    # 遍历当前目录下的所有Python文件
    for filename in os.listdir(current_dir):
        if (filename.endswith('.py') and 
            filename not in ('__init__.py', 'BaseTeleopGroup.py')):
            
            # 获取模块名（去掉.py后缀）
            module_name = filename[:-3]
            
            try:
                # 动态导入模块 - 使用相对导入路径
                module = importlib.import_module(f'.{module_name}', package='EasyTeleop.TeleopGroup')
                
                # 查找模块中的类（非基类且继承自BaseTeleopGroup）
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, module.BaseTeleopGroup) and 
                        attr != module.BaseTeleopGroup):
                        
                        # 获取类型名称并添加到字典中
                        type_name = attr.get_type_name()
                        teleop_group_classes[type_name] = attr
                        break
                        
            except Exception as e:
                print(f"导入模块 EasyTeleop.TeleopGroup.{module_name} 时出错: {e}")
    
    return teleop_group_classes