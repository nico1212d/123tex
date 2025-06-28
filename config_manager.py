import os
import shutil
import tomlkit
from dotenv import dotenv_values

try:
    from modules.MaiBot.src.common.logger import get_logger
    logger = get_logger("config_manager")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("config_manager")

# 配置文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "modules", "MaiBot", "config", "bot_config.toml")
CONFIG_BACKUP_PATH = f"{CONFIG_PATH}.bak"
LPMM_CONFIG_PATH = os.path.join(BASE_DIR, "modules", "MaiBot", "config", "lpmm_config.toml")
LPMM_BACKUP_PATH = f"{LPMM_CONFIG_PATH}.bak"
NAPCAT_CONFIG_PATH = os.path.join(BASE_DIR, "modules", "MaiBot-Napcat-Adapter", "config.toml")

def print_welcome():
    """显示欢迎信息"""
    print("=" * 60)
    print("欢迎使用 MaiBot 新手配置向导！（新版本适配）")
    print("=" * 60)
    print("本向导专为新手小白设计，8步即可完成新版本配置")
    print("提示：直接回车使用默认值，输入 Ctrl+C 退出")
    print("更多配置请使用一键包控制台中的\"快捷打开配置文件\"功能")
    print("=" * 60)
    print()

def get_yes_no_input(prompt, default=False):
    """获取是/否输入"""
    default_text = "是" if default else "否"
    user_input = input(f"{prompt} [是/否]（默认：{default_text}）：").strip().lower()
    
    if user_input in ['y', 'yes', '是', '1', 'true']:
        return True
    elif user_input in ['n', 'no', '否', '0', 'false']:
        return False
    else:
        return default

def get_number_input(prompt, default, min_val=None, max_val=None):
    """获取数字输入"""
    while True:
        user_input = input(f"{prompt}（默认：{default}）：").strip()
        
        if not user_input:
            return default
            
        try:
            value = float(user_input)
            if min_val is not None and value < min_val:
                print(f"输入值不能小于 {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"输入值不能大于 {max_val}")
                continue
            return int(value) if value.is_integer() else value
        except ValueError:
            print("请输入有效的数字")

def get_text_input(prompt, default="", required=False):
    """获取文本输入"""
    while True:
        user_input = input(f"{prompt}（当前：{default}）：").strip()
        
        if not user_input:
            if required and not default:
                print("此项为必填项，请输入内容")
                continue
            return default or ""
        
        return user_input

def backup_config():
    """备份配置文件"""
    try:
        if os.path.exists(CONFIG_PATH) and not os.path.exists(CONFIG_BACKUP_PATH):
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            shutil.copy(CONFIG_PATH, CONFIG_BACKUP_PATH)
            logger.info(f"已创建配置文件备份：{CONFIG_BACKUP_PATH}")
        else:
            logger.info("配置备份文件已存在，跳过备份")
        if os.path.exists(LPMM_CONFIG_PATH) and not os.path.exists(LPMM_BACKUP_PATH):
            os.makedirs(os.path.dirname(LPMM_CONFIG_PATH), exist_ok=True)
            shutil.copy(LPMM_CONFIG_PATH, LPMM_BACKUP_PATH)
            logger.info(f"已创建LPMM配置文件备份：{LPMM_BACKUP_PATH}")
        else:
            logger.info("LPMM配置备份文件已存在，跳过备份")
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")
        raise

def load_config():
    """加载配置文件"""
    try:
        if not os.path.exists(CONFIG_PATH):
            # 尝试从模板创建配置文件
            template_path = os.path.join(BASE_DIR, "modules", "MaiBot", "template", "bot_config_template.toml")
            if os.path.exists(template_path):
                config_dir = os.path.dirname(CONFIG_PATH)
                os.makedirs(config_dir, exist_ok=True)
                shutil.copy2(template_path, CONFIG_PATH)
                logger.info(f"已从模板创建配置文件: {CONFIG_PATH}")
            else:
                logger.error(f"找不到配置文件和模板文件 {CONFIG_PATH}")
                raise FileNotFoundError(f"配置文件 {CONFIG_PATH} 未找到")
        
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return tomlkit.load(f)
            
    except tomlkit.exceptions.TOMLKitError as e:
        logger.error(f"配置文件格式错误: {str(e)}")
        raise Exception(f"配置文件格式错误，请检查文件语法：{str(e)}")
    except Exception as e:
        logger.error(f"读取配置失败: {str(e)}")
        raise

def save_config(config):
    """保存配置文件"""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            tomlkit.dump(config, f)
        logger.info("配置文件已保存")
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        raise

def ensure_lpmm_config_exists():
    """确保LPMM配置文件存在"""
    if not os.path.exists(LPMM_CONFIG_PATH):
        template_path = os.path.join(BASE_DIR, "modules", "MaiBot", "template", "lpmm_config_template.toml")
        config_dir = os.path.dirname(LPMM_CONFIG_PATH)
        os.makedirs(config_dir, exist_ok=True)
        
        if os.path.exists(template_path):
            shutil.copy2(template_path, LPMM_CONFIG_PATH)
            logger.info(f"已从模板创建LPMM配置文件: {LPMM_CONFIG_PATH}")
        else:
            # 创建基本配置文件
            basic_config = tomlkit.document()
            basic_config["info_extraction"] = {"workers": 10}
            basic_config["llm_providers"] = []
            with open(LPMM_CONFIG_PATH, "w", encoding="utf-8") as f:
                tomlkit.dump(basic_config, f)
            logger.info(f"已创建基本LPMM配置文件: {LPMM_CONFIG_PATH}")

def step_basic_info(config):
    """配置基本信息"""
    print("\n=== 第1步：配置机器人基本信息 ===")
    
    # 配置QQ账号和昵称
    bot_config = config.setdefault('bot', {})
    
    # QQ账号配置
    current_qq = bot_config.get('qq_account', '')
    if current_qq:
        print(f"当前QQ账号：{current_qq}")
        if not get_yes_no_input("是否更换QQ账号", False):
            pass
        else:
            qq_account = get_text_input("请输入机器人的QQ账号", str(current_qq), required=True)
            try:
                bot_config['qq_account'] = int(qq_account)
            except ValueError:
                print("QQ账号必须是数字，使用默认值")
                bot_config['qq_account'] = current_qq or 1145141919810
    else:
        qq_account = get_text_input("请输入机器人的QQ账号", "1145141919810", required=True)
        try:
            bot_config['qq_account'] = int(qq_account)
        except ValueError:
            print("QQ账号必须是数字，使用默认值")
            bot_config['qq_account'] = 1145141919810
    
    # 昵称配置
    current_nickname = bot_config.get('nickname', '麦麦')
    nickname = get_text_input("请输入机器人的昵称", current_nickname)
    bot_config['nickname'] = nickname
    
    # 别名配置
    if get_yes_no_input("是否配置机器人别名", True):
        current_aliases = bot_config.get('alias_names', ["麦叠", "牢麦"])
        bot_config['alias_names'] = get_list_input(
            "配置机器人别名（用户可以用这些名字称呼机器人）",
            current_aliases,
            "别名",
            allow_empty=False
        )
    else:
        bot_config['alias_names'] = bot_config.get('alias_names', ["麦叠", "牢麦"])
    
    print(f"机器人信息已设置：{nickname} (QQ: {bot_config['qq_account']})")
    print(f"   别名: {', '.join(bot_config['alias_names'])}")
    return config

def step_personality(config):
    """配置人格设定"""
    print("\n=== 第2步：配置机器人人格 ===")
    print("提示：这决定了机器人的说话风格和性格特点")
    
    personality = config.setdefault('personality', {})
    
    # 主人格描述
    current_core = personality.get('personality_core', '是一个积极向上的女大学生')
    core = get_text_input("请输入机器人的基本人格描述（建议50字以内）", current_core)
    personality['personality_core'] = core
    
    # 人格细节配置
    if get_yes_no_input("是否配置详细的人格特点", False):
        current_sides = personality.get('personality_sides', [
            "友善热情，乐于助人",
            "说话风格轻松自然",
            "有一定的幽默感"
        ])
        personality['personality_sides'] = get_list_input(
            "配置人格特点（描述机器人性格的各个方面）",
            current_sides,
            "人格特点",
            allow_empty=False
        )
    else:
        personality['personality_sides'] = personality.get('personality_sides', [
            "友善热情，乐于助人",
            "说话风格轻松自然",
            "有一定的幽默感"
        ])
    
    # 人格压缩设置
    personality['compress_personality'] = get_yes_no_input("是否压缩人格信息（节省token，但会丢失细节）", False)
    
    config['personality'] = personality
    print(f"机器人人格已设置：{core}")
    return config

def step_identity(config):
    """配置身份特征"""
    print("\n=== 第3步：配置机器人身份特征 ===")
    print("提示：包括外貌、性别、身高、职业等详细信息")
    
    identity = config.setdefault('identity', {})
    
    # 身份特征配置（根据新版本配置文件，这应该是一个列表）
    if get_yes_no_input("是否配置详细的身份特征", True):
        current_details = identity.get('identity_detail', [
            "年龄为19岁",
            "是女孩子", 
            "身高为160cm",
            "有橙色的短发"
        ])
        identity['identity_detail'] = get_list_input(
            "配置身份特征（描述机器人的外貌、属性等）",
            current_details,
            "身份特征",
            allow_empty=False
        )
    else:
        identity['identity_detail'] = identity.get('identity_detail', [
            "年龄为19岁",
            "是女孩子",
            "身高为160cm", 
            "有橙色的短发"
        ])
    
    # 身份压缩设置
    identity['compress_indentity'] = get_yes_no_input("是否压缩身份信息（节省token，推荐开启）", True)
    
    config['identity'] = identity
    print("身份特征已设置")
    return config

def step_expression(config):
    """配置表达方式"""
    print("\n=== 第4步：配置表达方式 ===")
    print("提示：控制机器人的表达风格和学习能力")
    
    expression = config.setdefault('expression', {})
    
    # 表达学习功能
    print("表达学习设置：")
    expression['learn_expression'] = get_yes_no_input("启用表达学习（机器人会学习用户的表达方式）", True)
    
    if expression['learn_expression']:
        expression['expression_window'] = get_number_input("表达学习窗口大小", 10, 5, 50)
        expression['max_expression_count'] = get_number_input("最大学习表达数量", 30, 10, 100)
        expression['learn_expression_threshold'] = get_number_input("学习阈值（0-1，越高学习越保守）", 0.7, 0.1, 1.0)
    
    config['expression'] = expression
    print("表达方式配置完成")
    return config

def step_chat_mode(config):
    """配置聊天模式"""
    print("\n=== 第5步：配置聊天模式 ===")
    print("聊天模式说明：")
    print("   • normal（普通模式）：适中的回复频率，推荐新手使用")
    print("   • focus（专注模式）：更频繁的回复，消耗更多token")
    print("   • auto（自动模式）：智能切换，需要一定经验")
    
    # 基础聊天配置
    chat = config.setdefault('chat', {})
    
    while True:
        mode = input("请选择聊天模式 [normal/focus/auto]（默认：normal）：").strip().lower() or 'normal'
        
        if mode in ['normal', 'focus', 'auto']:
            chat['chat_mode'] = mode
            break
        else:
            print("请输入有效的模式：normal、focus 或 auto")
    
    # 时段回复频率设置（新功能）
    print("\n配置时段回复频率（不同时间段的活跃程度）：")
    time_based = get_yes_no_input("是否配置不同时段的回复频率", False)
    
    if time_based:
        # 简化时段配置
        morning_freq = get_number_input("早晨活跃度（6:00-12:00）", 0.8, 0.1, 2.0)
        afternoon_freq = get_number_input("下午活跃度（12:00-18:00）", 1.0, 0.1, 2.0)
        evening_freq = get_number_input("晚上活跃度（18:00-24:00）", 1.2, 0.1, 2.0)
        night_freq = get_number_input("深夜活跃度（0:00-6:00）", 0.3, 0.1, 2.0)
        
        chat['time_frequency'] = {
            "6-12": morning_freq,
            "12-18": afternoon_freq, 
            "18-24": evening_freq,
            "0-6": night_freq
        }
    else:
        # 使用全天统一频率
        talk_freq = get_number_input("统一回复频率（1为正常，越高越活跃）", 1.0, 0.1, 5.0)
        chat['talk_frequency'] = talk_freq
    
    # 自动模式配置
    if mode == 'auto':
        print("\n配置自动切换参数：")
        auto_threshold = get_number_input("进入专注模式的阈值（0-2，越小越容易进入）", 1.0, 0, 2)
        exit_threshold = get_number_input("退出专注模式的阈值（0-2，越小越容易退出）", 1.0, 0, 2)
        
        chat['auto_focus_threshold'] = auto_threshold
        chat['exit_focus_threshold'] = exit_threshold
    
    # Normal Chat 配置
    normal_chat = config.setdefault('normal_chat', {})
    normal_chat['enable_random_chat'] = get_yes_no_input("启用随机主动聊天", True)
    if normal_chat['enable_random_chat']:
        normal_chat['random_chat_probability'] = get_number_input("主动聊天概率（0-1）", 0.1, 0, 1)
        normal_chat['random_chat_interval'] = get_number_input("主动聊天间隔（分钟）", 30, 5, 180)
    
    # Focus Chat 配置
    focus_chat = config.setdefault('focus_chat', {})
    focus_chat['max_focus_duration'] = get_number_input("专注模式最大持续时间（分钟）", 30, 5, 120)
    focus_chat['focus_exit_probability'] = get_number_input("专注模式退出概率（0-1）", 0.1, 0, 1)
    
    config['chat'] = chat
    config['normal_chat'] = normal_chat
    config['focus_chat'] = focus_chat
    
    print(f"聊天模式已设置为：{mode}")
    return config

def step_groups(config):
    """配置群聊权限"""
    print("\n=== 第6步：配置可发消息的群聊 ===")
    print("提示：只有在此列表中的群聊，机器人才会发送消息")
    
    # 尝试从适配器配置中获取当前群组列表
    current_groups = []
    try:
        if os.path.exists(NAPCAT_CONFIG_PATH):
            with open(NAPCAT_CONFIG_PATH, "r", encoding="utf-8") as f:
                napcat_config = tomlkit.load(f)
            current_groups = napcat_config.get('Chat', {}).get('group_list', [])
    except Exception as e:
        logger.warning(f"无法读取适配器配置: {str(e)}")
    
    # 使用交互式配置
    groups = get_group_list_input(
        "配置机器人可发消息的群聊",
        current_groups
    )
    
    if groups:
        # 更新 MaiBot-Napcat-Adapter 配置
        try:
            if os.path.exists(NAPCAT_CONFIG_PATH):
                with open(NAPCAT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    napcat_config = tomlkit.load(f)
                
                chat_config = napcat_config.setdefault('Chat', {})
                chat_config['group_list'] = groups
                
                with open(NAPCAT_CONFIG_PATH, "w", encoding="utf-8") as f:
                    tomlkit.dump(napcat_config, f)
                logger.info("已配置群组到MaiBot-Napcat-Adapter")
                print(f"已配置 {len(groups)} 个群聊")
            else:
                logger.warning(f"未找到适配器配置文件: {NAPCAT_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"配置适配器失败: {str(e)}")
    else:
        print("未配置任何群聊，机器人将不会主动发送消息")
    
    return config

def step_api_key(config):
    """配置API密钥"""
    print("\n=== 第7步：配置API密钥 ===")
    print("请前往 https://cloud.siliconflow.cn/account/ak 获取免费API密钥")
    print("这是必需的，机器人需要API密钥才能正常工作")
    
    env_path = os.path.join(BASE_DIR, "modules", "MaiBot", ".env")
    current_env = dotenv_values(env_path) if os.path.exists(env_path) else {}
    current_key = current_env.get("SILICONFLOW_KEY", "")
    
    if current_key:
        print(f"当前已配置API密钥：{current_key[:8]}...{current_key[-4:] if len(current_key) > 12 else current_key}")
        if not get_yes_no_input("是否更换API密钥", False):
            return config
    
    new_key = get_text_input("请输入SILICONFLOW API密钥", "", required=True)
    
    if new_key:
        try:
            # 保存到环境变量文件
            env_dir = os.path.dirname(env_path)
            os.makedirs(env_dir, exist_ok=True)
            
            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()
            
            # 更新或添加 API 密钥
            found = False
            for i, line in enumerate(env_lines):
                if line.startswith("SILICONFLOW_KEY="):
                    env_lines[i] = f"SILICONFLOW_KEY={new_key}\n"
                    found = True
                    break
            
            if not found:
                env_lines.append(f"\nSILICONFLOW_KEY={new_key}\n")
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            
            # 同步到 LPMM 配置
            ensure_lpmm_config_exists()
            with open(LPMM_CONFIG_PATH, "r", encoding="utf-8") as f:
                lpmm_data = tomlkit.load(f)
            
            providers = lpmm_data.setdefault("llm_providers", [])
            
            # 更新或添加 SiliconFlow 提供商
            updated = False
            for provider in providers:
                if provider.get("name") == "siliconflow":
                    provider["api_key"] = new_key
                    updated = True
                    break
            
            if not updated:
                providers.append({
                    "name": "siliconflow",
                    "base_url": "https://api.siliconflow.cn/v1/",
                    "api_key": new_key
                })
            
            with open(LPMM_CONFIG_PATH, "w", encoding="utf-8") as f:
                tomlkit.dump(lpmm_data, f)
            
            logger.info("API密钥配置成功")
            print("API密钥配置成功")
            
        except Exception as e:
            logger.error(f"API密钥配置失败: {str(e)}")
            print(f"API密钥配置失败: {str(e)}")
    
    return config

def step_advanced_settings(config):
    """高级设置（可选）"""
    print("\n=== 第8步：高级设置（可选）===")
    
    if not get_yes_no_input("是否配置高级设置", False):
        print("跳过高级设置，使用推荐默认配置")
        
        # 设置新版本重要的默认值
        config.setdefault('emoji', {
            'max_reg_num': 60,
            'do_replace': True,
            'steal_emoji': True,
            'check_interval': 10
        })
        
        config.setdefault('memory', {'enable_memory': True})
        config.setdefault('relationship', {'enable_relationship': True})
        config.setdefault('lpmm_knowledge', {'enable': True})
        config.setdefault('chinese_typo', {'enable': True})
        config.setdefault('response_post_process', {'enable_response_post_process': True})
        config.setdefault('mood', {'enable_mood': False})  # 新功能默认关闭
        config.setdefault('keyword_reaction', {'enable': False})  # 新功能默认关闭
        config.setdefault('experimental', {
            'enable_friend_chat': False,
            'debug_show_chat_mode': False
        })
        
        # 新增配置项默认值
        config.setdefault('message_receive', {
            'enable_at_filter': True,
            'enable_keyword_filter': False
        })
        
        config.setdefault('focus_chat_processor', {
            'enable_processor': True,
            'processor_threshold': 0.8
        })
        
        config.setdefault('response_splitter', {
            'enable_split': True,
            'max_length': 500,
            'split_strategy': 'smart'
        })
        
        config.setdefault('model', {
            'default_model': 'Qwen/Qwen2.5-7B-Instruct',
            'temperature': 0.7,
            'max_tokens': 2048
        })
        
        config.setdefault('log', {
            'level': 'INFO',
            'enable_file_log': True,
            'max_log_files': 10
        })
        
        return config
    
    print("\n配置表情包设置：")
    emoji = config.setdefault('emoji', {})
    emoji['max_reg_num'] = get_number_input("表情包最大数量", 60, 10, 200)
    emoji['do_replace'] = get_yes_no_input("达到最大数量时自动替换旧表情包", True)
    emoji['steal_emoji'] = get_yes_no_input("是否学习其他人的表情包", True)
    emoji['check_interval'] = get_number_input("表情包检查间隔（分钟）", 10, 1, 60)
    
    print("\n配置记忆和学习：")
    memory = config.setdefault('memory', {})
    memory['enable_memory'] = get_yes_no_input("启用记忆系统（让机器人能记住对话）", True)
    
    relationship = config.setdefault('relationship', {})
    relationship['enable_relationship'] = get_yes_no_input("启用关系系统（让机器人记住与用户的关系）", True)
    
    print("\n配置情绪和反应系统：")
    mood = config.setdefault('mood', {})
    mood['enable_mood'] = get_yes_no_input("启用情绪系统（让机器人有情绪变化）", False)
    
    keyword_reaction = config.setdefault('keyword_reaction', {})
    keyword_reaction['enable'] = get_yes_no_input("启用关键词反应系统", False)
    
    print("\n配置回复处理：")
    chinese_typo = config.setdefault('chinese_typo', {})
    chinese_typo['enable'] = get_yes_no_input("启用中文错别字生成器（让对话更自然）", True)
    
    response_post_process = config.setdefault('response_post_process', {})
    response_post_process['enable_response_post_process'] = get_yes_no_input("启用回复后处理", True)
    
    response_splitter = config.setdefault('response_splitter', {})
    response_splitter['enable_split'] = get_yes_no_input("启用消息分割（长消息自动分段）", True)
    if response_splitter['enable_split']:
        response_splitter['max_length'] = get_number_input("消息分割长度", 500, 100, 2000)
    
    print("\n配置实验性功能：")
    experimental = config.setdefault('experimental', {})
    experimental['enable_friend_chat'] = get_yes_no_input("启用私聊功能", False)
    experimental['debug_show_chat_mode'] = get_yes_no_input("显示聊天模式调试信息", False)
    
    print("\n配置消息过滤：")
    message_receive = config.setdefault('message_receive', {})
    message_receive['enable_at_filter'] = get_yes_no_input("启用@过滤（只回复@消息）", True)
    message_receive['enable_keyword_filter'] = get_yes_no_input("启用关键词过滤", False)
    print("高级设置配置完成")
    return config

def get_list_input(prompt, current_list=None, item_name="项目", allow_empty=False):
    """
    通用的列表交互式输入函数
    
    Args:
        prompt: 配置提示文字
        current_list: 当前已有的列表
        item_name: 项目类型名称（如"别名"、"人格特点"等）
        allow_empty: 是否允许空列表
    
    Returns:
        list: 配置后的列表
    """
    if current_list is None:
        current_list = []
    
    result_list = current_list.copy()
    
    print(f"\n{prompt}")
    if result_list:
        print(f"当前已有{item_name}：")
        for i, item in enumerate(result_list, 1):
            print(f"  {i}. {item}")
    else:
        print(f"当前没有{item_name}")
    
    print("\n操作说明：")
    print(f"  • 输入 'a' 或 'add' - 添加{item_name}")
    print(f"  • 输入 'd' 或 'del' - 删除{item_name}")
    print(f"  • 输入 'l' 或 'list' - 查看当前{item_name}")
    print("  • 直接回车 - 完成配置")
    print("  • 输入 'help' - 显示帮助")
    
    while True:
        try:
            command = input("\n请选择操作 [a添加/d删除/l查看/回车完成]: ").strip().lower()
            
            if not command:
                # 检查是否允许空列表
                if not allow_empty and not result_list:
                    print(f"{item_name}不能为空，请至少添加一个")
                    continue
                break
                
            elif command in ['a', 'add', '添加']:
                item = input(f"请输入新的{item_name}: ").strip()
                if item:
                    if item not in result_list:
                        result_list.append(item)
                        print(f"已添加{item_name}: {item}")
                    else:
                        print(f"{item_name} '{item}' 已存在")
                else:
                    print("输入不能为空")
                    
            elif command in ['d', 'del', 'delete', '删除']:
                if not result_list:
                    print(f"当前没有{item_name}可删除")
                    continue
                
                print(f"当前{item_name}列表：")
                for i, item in enumerate(result_list, 1):
                    print(f"  {i}. {item}")
                
                try:
                    choice = input(f"请输入要删除的{item_name}序号 (1-{len(result_list)}): ").strip()
                    if choice.isdigit():
                        index = int(choice) - 1
                        if 0 <= index < len(result_list):
                            removed_item = result_list.pop(index)
                            print(f"已删除{item_name}: {removed_item}")
                        else:
                            print("序号超出范围")
                    else:
                        print("请输入有效的数字")
                except ValueError:
                    print("请输入有效的数字")
                    
            elif command in ['l', 'list', '查看']:
                if result_list:
                    print(f"当前{item_name}列表：")
                    for i, item in enumerate(result_list, 1):
                        print(f"  {i}. {item}")
                else:
                    print(f"当前没有{item_name}")
                    
            elif command in ['help', '帮助']:
                print("\n操作帮助：")
                print(f"  • a/add/添加 - 添加新的{item_name}")
                print(f"  • d/del/删除 - 删除现有{item_name}")
                print(f"  • l/list/查看 - 查看当前所有{item_name}")
                print(f"  • 直接回车 - 完成{item_name}配置")
                
            else:
                print("无效的命令，请输入 'help' 查看帮助")
                
        except KeyboardInterrupt:
            print(f"\n{item_name}配置已取消")
            break
        except Exception as e:
            print(f"操作出错: {str(e)}")
    
    return result_list

def get_group_list_input(prompt, current_list=None):
    """
    群组列表专用配置函数
    
    Args:
        prompt: 配置提示文字
        current_list: 当前已有的群组列表
    
    Returns:
        list: 配置后的群组列表
    """
    if current_list is None:
        current_list = []
    
    result_list = current_list.copy()
    
    print(f"\n{prompt}")
    if result_list:
        print("当前已配置群聊：")
        for i, group_id in enumerate(result_list, 1):
            print(f"  {i}. {group_id}")
    else:
        print("当前没有配置任何群聊")
    
    print("\n操作说明:")
    print("  • 输入 'a' 或 'add' - 添加群聊")
    print("  • 输入 'd' 或 'del' - 删除群聊")
    print("  • 输入 'l' 或 'list' - 查看当前群聊")
    print("  • 直接回车 - 完成配置")
    print("  • 输入 'help' - 显示帮助")
    
    while True:
        try:
            command = input("\n请选择操作 [a添加/d删除/l查看/回车完成]: ").strip().lower()
            
            if not command:
                break
                
            elif command in ['a', 'add', '添加']:
                group_input = input("请输入群号: ").strip()
                if group_input.isdigit():
                    group_id = int(group_input)
                    if group_id not in result_list:
                        result_list.append(group_id)
                        print(f"已添加群聊: {group_id}")
                    else:
                        print(f"群聊 {group_id} 已存在")
                else:
                    print("请输入有效的数字群号")
                    
            elif command in ['d', 'del', 'delete', '删除']:
                if not result_list:
                    print("当前没有群聊可删除")
                    continue
                
                print("当前群聊列表：")
                for i, group_id in enumerate(result_list, 1):
                    print(f"  {i}. {group_id}")
                
                try:
                    choice = input(f"请输入要删除的群聊序号 (1-{len(result_list)}): ").strip()
                    if choice.isdigit():
                        index = int(choice) - 1
                        if 0 <= index < len(result_list):
                            removed_group = result_list.pop(index)
                            print(f"已删除群聊: {removed_group}")
                        else:
                            print("序号超出范围")
                    else:
                        print("请输入有效的数字")
                except ValueError:
                    print("请输入有效的数字")
                    
            elif command in ['l', 'list', '查看']:
                if result_list:
                    print("当前群聊列表：")
                    for i, group_id in enumerate(result_list, 1):
                        print(f"  {i}. {group_id}")
                else:
                    print("当前没有配置任何群聊")
                    
            elif command in ['help', '帮助']:
                print("\n操作帮助:")
                print("  • a/add/添加 - 添加新的群聊")
                print("  • d/del/删除 - 删除现有群聊")
                print("  • l/list/查看 - 查看当前所有群聊")
                print("  • 直接回车 - 完成群聊配置")
                
            else:
                print("无效的命令，请输入 'help' 查看帮助")
                
        except KeyboardInterrupt:
            print("\n群聊配置已取消")
            break
        except Exception as e:
            print(f"操作出错: {str(e)}")
    
    return result_list

def main():
    """主配置流程"""
    try:
        print_welcome()
        
        # 备份配置
        backup_config()
        
        # 加载配置
        config = load_config()
        
        # 执行配置步骤（新版本流程）
        config = step_basic_info(config)         # 第1步：基本信息
        config = step_personality(config)        # 第2步：人格设定
        config = step_identity(config)           # 第3步：身份特征
        config = step_expression(config)         # 第4步：表达方式
        config = step_chat_mode(config)          # 第5步：聊天模式
        config = step_groups(config)             # 第6步：群聊权限
        config = step_api_key(config)            # 第7步：API密钥
        config = step_advanced_settings(config)  # 第8步：高级设置
        
        # 保存配置
        save_config(config)
        
        print("\n" + "=" * 60)
        print("新版本 MaiBot 配置完成！")
        print("=" * 60)
        print("所有配置已保存成功")
        print("现在可以启动 MaiBot 了")
        print("更多配置请使用一键包控制台中的\"快捷打开配置文件\"功能")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n配置已取消")
        print("下次启动时可以重新配置")
    except Exception as e:
        logger.error(f"配置过程出现错误: {str(e)}")
        print(f"\n配置失败: {str(e)}")
        print("请检查错误信息或寻求帮助")

if __name__ == "__main__":
    main()
