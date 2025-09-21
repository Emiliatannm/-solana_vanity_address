import threading
import os
import time
import secrets
from tqdm import tqdm
from mnemonic import Mnemonic
import hashlib
import hmac
from typing import List

try:
    import base58
except ImportError:
    print("错误：需要安装 base58 库 / Error: Need to install base58 library")
    print("请运行: pip install base58 / Please run: pip install base58")
    input("按回车退出... / Press Enter to exit...")
    exit(1)

try:
    from nacl.signing import SigningKey
    from nacl.encoding import RawEncoder
except ImportError:
    print("错误：需要安装 PyNaCl 库 / Error: Need to install PyNaCl library")
    print("请运行: pip install pynacl / Please run: pip install pynacl")
    input("按回车退出... / Press Enter to exit...")
    exit(1)

# 全局变量
found_count = 0
lock = threading.Lock()
total_attempts = 0
start_time = 0

def create_solana_keypair():
    """创建Solana密钥对"""
    # 生成32字节随机私钥
    private_key = secrets.token_bytes(32)
    
    # 使用Ed25519创建签名密钥
    signing_key = SigningKey(private_key)
    
    # 获取公钥
    public_key = signing_key.verify_key.encode()
    
    # 生成Base58格式的地址
    address = base58.b58encode(public_key).decode('utf-8')
    
    return private_key, address

def derive_keypair_from_mnemonic(mnemonic_words: str):
    """从助记词派生Solana密钥对 - 使用正确的BIP44路径"""
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(mnemonic_words)
    
    # 使用正确的BIP44派生路径：m/44'/501'/0'/0'
    # 501是Solana的coin type
    
    # 第一步：从种子派生主密钥
    master_key = hmac.new(b"ed25519 seed", seed, hashlib.sha512).digest()
    master_private_key = master_key[:32]
    master_chain_code = master_key[32:]
    
    def derive_child_key(parent_key, parent_chain_code, index):
        """派生子密钥"""
        if index >= 0x80000000:  # 硬化派生
            data = b'\x00' + parent_key + index.to_bytes(4, 'big')
        else:  # 非硬化派生
            # 对于ed25519，我们简化处理
            data = b'\x00' + parent_key + index.to_bytes(4, 'big')
        
        hmac_result = hmac.new(parent_chain_code, data, hashlib.sha512).digest()
        child_key = hmac_result[:32]
        child_chain_code = hmac_result[32:]
        return child_key, child_chain_code
    
    try:
        # m/44' (硬化)
        key, chain_code = derive_child_key(master_private_key, master_chain_code, 44 + 0x80000000)
        
        # m/44'/501' (硬化)
        key, chain_code = derive_child_key(key, chain_code, 501 + 0x80000000)
        
        # m/44'/501'/0' (硬化)
        key, chain_code = derive_child_key(key, chain_code, 0 + 0x80000000)
        
        # m/44'/501'/0'/0' (硬化)
        private_key, _ = derive_child_key(key, chain_code, 0 + 0x80000000)
        
        # 创建签名密钥
        signing_key = SigningKey(private_key)
        public_key = signing_key.verify_key.encode()
        address = base58.b58encode(public_key).decode('utf-8')
        
        return private_key, address
        
    except Exception:
        # 如果BIP44派生失败，使用更简单的方法
        # 直接对助记词进行哈希
        seed_hash = hashlib.sha256(mnemonic_words.encode()).digest()
        private_key = seed_hash[:32]
        
        signing_key = SigningKey(private_key)
        public_key = signing_key.verify_key.encode()
        address = base58.b58encode(public_key).decode('utf-8')
        
        return private_key, address

# 验证输入字符是否为有效的Base58字符
def validate_base58(text: str) -> bool:
    """验证字符串是否只包含有效的Base58字符"""
    base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return all(c in base58_chars for c in text)

# 语言选择
print("=== SOL靓号生成器 / SOL Vanity Address Generator ===")
print("Please select language / 请选择语言:")
print("1. 中文")
print("2. English")

while True:
    lang_choice = input("选择语言 / Choose language (1/2): ").strip()
    if lang_choice in ["1", "2"]:
        use_chinese = lang_choice == "1"
        break
    print("输入错误，请输入 1 或 2 / Invalid input, please enter 1 or 2.")

# 根据语言设置文本
if use_chinese:
    texts = {
        'title': "=== SOL靓号生成器 ===",
        'description': [
            "说明：",
            "1. 助记词生成：可以恢复账户，用助记词可生成全链地址。",
            "2. 私钥生成：速度更快，但只有SOL单链私钥，无法恢复助记词。",
            "前缀/后缀匹配严格区分大小写，请按实际字符输入。",
            "注意：Solana地址使用Base58编码，有效字符为：123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        ],
        'choose_method': "请选择生成方式：1=助记词生成，2=私钥生成: ",
        'input_error': "输入错误，请输入 1 或 2。",
        'input_prefix': "请输入地址前缀(区分大小写，如 Sol1)：",
        'input_suffix': "请输入地址后缀(区分大小写，如 AAaA)：",
        'prefix_invalid': "前缀包含无效的Base58字符，请重新输入！",
        'suffix_invalid': "后缀包含无效的Base58字符，请重新输入！",
        'empty_error': "前缀和后缀不能都为空！",
        'input_count': "请输入要生成的靓号数量：",
        'input_threads': "请输入线程数（默认 {}）：",
        'progress_desc': "已尝试次数",
        'progress_unit': "次",
        'eta_remaining': "估计剩余",
        'found_vanity': "🎉 找到第 {} 个SOL靓号！",
        'address': "地址: {}",
        'mnemonic': "助记词: {}",
        'private_key_phantom': "私钥(Phantom等主流钱包): {}",
        'private_key_solflare': "私钥(Solflare钱包): {}",
        'file_entry': "=== 第 {} 个SOL靓号 ===",
        'wallet_instructions': [
            "导入说明:",
            "- Phantom等主流钱包: 使用上面的Phantom格式",
            "- Solflare钱包: 使用Solflare格式",
            "- Sollet钱包: 使用bytes数组格式"
        ],
        'start_generation': "开始生成，使用 {} 个线程...",
        'target_info': "目标前缀: '{}', 目标后缀: '{}'",
        'target_count': "目标数量: {}",
        'user_interrupt': "⚠️ 用户中断，已生成 {} 个靓号",
        'generation_complete': "✨ 已生成 {} 个SOL靓号，结果保存到文件: {}",
        'total_attempts': "总尝试次数: {:,}",
        'avg_attempts': "平均每个靓号需要尝试: {:,} 次",
        'total_time': "总耗时: {:.1f} 秒",
        'program_error': "❌ 程序运行出错: {}",
        'error_type': "错误类型: {}",
        'error_details': "详细错误信息:",
        'press_enter': "按回车退出程序…",
        'calculating': "计算中"
    }
else:
    texts = {
        'title': "=== SOL Vanity Address Generator ===",
        'description': [
            "Description:",
            "1. Mnemonic generation: Can recover account, mnemonic can generate cross-chain addresses.",
            "2. Private key generation: Faster, but only SOL single-chain private key, cannot recover mnemonic.",
            "Prefix/suffix matching is case-sensitive, please enter actual characters.",
            "Note: Solana addresses use Base58 encoding, valid characters: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        ],
        'choose_method': "Please choose generation method: 1=Mnemonic, 2=Private key: ",
        'input_error': "Invalid input, please enter 1 or 2.",
        'input_prefix': "Enter address prefix (case-sensitive, e.g. Sol1): ",
        'input_suffix': "Enter address suffix (case-sensitive, e.g. AAaA): ",
        'prefix_invalid': "Prefix contains invalid Base58 characters, please re-enter!",
        'suffix_invalid': "Suffix contains invalid Base58 characters, please re-enter!",
        'empty_error': "Prefix and suffix cannot both be empty!",
        'input_count': "Enter number of vanity addresses to generate: ",
        'input_threads': "Enter number of threads (default {}): ",
        'progress_desc': "Attempts made",
        'progress_unit': "times",
        'eta_remaining': "ETA",
        'found_vanity': "🎉 Found SOL vanity address #{}!",
        'address': "Address: {}",
        'mnemonic': "Mnemonic: {}",
        'private_key_phantom': "Private key (Phantom & mainstream wallets): {}",
        'private_key_solflare': "Private key (Solflare wallet): {}",
        'file_entry': "=== SOL Vanity Address #{} ===",
        'wallet_instructions': [
            "Import instructions:",
            "- Phantom & mainstream wallets: Use Phantom format above",
            "- Solflare wallet: Use Solflare format",
            "- Sollet wallet: Use bytes array format"
        ],
        'start_generation': "Starting generation with {} threads...",
        'target_info': "Target prefix: '{}', Target suffix: '{}'",
        'target_count': "Target count: {}",
        'user_interrupt': "⚠️ User interrupted, generated {} vanity addresses",
        'generation_complete': "✨ Generated {} SOL vanity addresses, saved to file: {}",
        'total_attempts': "Total attempts: {:,}",
        'avg_attempts': "Average attempts per vanity address: {:,}",
        'total_time': "Total time: {:.1f} seconds",
        'program_error': "❌ Program error: {}",
        'error_type': "Error type: {}",
        'error_details': "Detailed error information:",
        'press_enter': "Press Enter to exit...",
        'calculating': "calculating"
    }

# 显示说明
print(texts['title'])
for line in texts['description']:
    print(line)
print()

try:
    # 用户选择生成方式
    while True:
        choice = input(texts['choose_method']).strip()
        if choice in ["1", "2"]:
            use_mnemonic = choice == "1"
            break
        print(texts['input_error'])

    # 用户输入前缀、后缀和数量
    while True:
        TARGET_PREFIX = input(texts['input_prefix']).strip()
        if not TARGET_PREFIX or validate_base58(TARGET_PREFIX):
            break
        print(texts['prefix_invalid'])

    while True:
        TARGET_SUFFIX = input(texts['input_suffix']).strip()
        if not TARGET_SUFFIX or validate_base58(TARGET_SUFFIX):
            break
        print(texts['suffix_invalid'])

    if not TARGET_PREFIX and not TARGET_SUFFIX:
        print(texts['empty_error'])
        input(texts['press_enter'])
        exit(1)

    TARGET_COUNT = int(input(texts['input_count']).strip())

    # 线程数输入
    CPU_CORES = os.cpu_count() or 4
    THREADS_INPUT = input(texts['input_threads'].format(CPU_CORES)).strip()
    THREADS = int(THREADS_INPUT) if THREADS_INPUT.isdigit() and int(THREADS_INPUT) > 0 else CPU_CORES

    # 助记词初始化
    mnemo = Mnemonic("english")

    # 保存文件名
    filename = f"solana_vanity_address_{int(time.time())}.txt"

    # 进度条 - 固定显示，不刷新描述
    progress_bar = tqdm(total=0, desc=texts['progress_desc'], ncols=80, unit=texts['progress_unit'])

    def update_progress():
        """更新进度条 - 考虑Base58大小写敏感性"""
        # Base58字符集大小为58，但需要考虑大小写敏感性
        base_probability = 1/58
        
        # 计算总长度
        total_length = len(TARGET_PREFIX) + len(TARGET_SUFFIX)
        basic_probability = base_probability ** total_length
        
        # 大小写敏感性修正因子
        case_sensitivity_factor = 1.0
        
        # 检查前缀和后缀的大小写复杂度
        if TARGET_PREFIX:
            has_upper = any(c.isupper() for c in TARGET_PREFIX if c.isalpha())
            has_lower = any(c.islower() for c in TARGET_PREFIX if c.isalpha())
            if has_upper and has_lower:
                case_sensitivity_factor *= 1.5  # 混合大小写更难
            elif has_upper or has_lower:
                case_sensitivity_factor *= 1.2  # 单一大小写稍难
        
        if TARGET_SUFFIX:
            has_upper = any(c.isupper() for c in TARGET_SUFFIX if c.isalpha())
            has_lower = any(c.islower() for c in TARGET_SUFFIX if c.isalpha())
            if has_upper and has_lower:
                case_sensitivity_factor *= 1.5
            elif has_upper or has_lower:
                case_sensitivity_factor *= 1.2
        
        # 应用大小写修正因子
        adjusted_probability = basic_probability / case_sensitivity_factor
        
        expected_total = int(1 / adjusted_probability)
        remaining = max(expected_total - total_attempts, 0)
        elapsed = time.time() - start_time
        speed = total_attempts / elapsed if elapsed > 0 else 0
        eta_sec = remaining / speed if speed > 0 else 0
        
        # 格式化剩余时间
        if eta_sec > 86400:  # 超过1天
            eta_str = f"{int(eta_sec/86400)}d {int((eta_sec%86400)/3600)}h"
        elif eta_sec > 3600:  # 超过1小时
            eta_str = f"{int(eta_sec/3600)}h {int((eta_sec%3600)/60)}m"
        elif eta_sec > 60:   # 超过1分钟
            eta_str = f"{int(eta_sec/60)}m"
        elif eta_sec > 0:    # 小于1分钟
            eta_str = f"{int(eta_sec)}s"
        else:
            eta_str = texts['calculating']
        
        progress_bar.set_postfix({texts['eta_remaining']: eta_str})

    # 批量生成函数
    def worker():
        global found_count, total_attempts
        
        while found_count < TARGET_COUNT:
            try:
                if use_mnemonic:
                    # 助记词生成模式
                    words = mnemo.generate(strength=128)
                    private_key, address = derive_keypair_from_mnemonic(words)
                else:
                    # 私钥生成模式
                    private_key, address = create_solana_keypair()
                    words = None
                
                with lock:
                    total_attempts += 1
                    progress_bar.update(1)
                    
                    # 每100次更新一次ETA
                    if total_attempts % 100 == 0:
                        update_progress()
                    
                    # 检查是否匹配
                    match = True
                    if TARGET_PREFIX and not address.startswith(TARGET_PREFIX):
                        match = False
                    if TARGET_SUFFIX and not address.endswith(TARGET_SUFFIX):
                        match = False
                        
                    if match:
                        found_count += 1
                        
                        # 私钥格式转换
                        private_key_hex = private_key.hex()
                        private_key_base58 = base58.b58encode(private_key).decode()
                        private_key_bytes = '[' + ', '.join(str(b) for b in private_key) + ']'
                        
                        # Phantom钱包格式 - 需要私钥+公钥的组合
                        signing_key = SigningKey(private_key)
                        public_key = signing_key.verify_key.encode()
                        phantom_format = base58.b58encode(private_key + public_key).decode()
                        
                        progress_bar.clear()
                        tqdm.write(f"\n{texts['found_vanity'].format(found_count)}")
                        tqdm.write(texts['address'].format(address))
                        if words:
                            tqdm.write(texts['mnemonic'].format(words))
                        tqdm.write(texts['private_key_phantom'].format(phantom_format))
                        tqdm.write(texts['private_key_solflare'].format(private_key_base58))
                        
                        # 保存到文件
                        with open(filename, "a", encoding="utf-8") as f:
                            f.write(f"{texts['file_entry'].format(found_count)}\n")
                            f.write(f"{texts['address'].format(address)}\n")
                            if words:
                                f.write(f"{texts['mnemonic'].format(words)}\n")
                            f.write(f"{texts['private_key_phantom'].format(phantom_format)}\n")
                            f.write(f"{texts['private_key_solflare'].format(private_key_base58)}\n")
                            f.write(f"Private key (hex): {private_key_hex}\n")
                            f.write(f"Private key (bytes): {private_key_bytes}\n")
                            for line in texts['wallet_instructions']:
                                f.write(f"{line}\n")
                            f.write(f"Generated time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        
                        if found_count >= TARGET_COUNT:
                            return
                            
            except Exception as e:
                # 生成失败时继续
                continue

    # 启动多线程
    print(f"\n{texts['start_generation'].format(THREADS)}")
    print(texts['target_info'].format(TARGET_PREFIX, TARGET_SUFFIX))
    print(texts['target_count'].format(TARGET_COUNT))
    print()

    # 记录开始时间
    start_time = time.time()

    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=worker, name=f"Worker-{i+1}")
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        # 等待所有线程完成
        for t in threads:
            t.join()
            
    except KeyboardInterrupt:
        print(f"\n\n{texts['user_interrupt'].format(found_count)}")

    progress_bar.close()
    print(f"\n{texts['generation_complete'].format(found_count, filename)}")
    print(texts['total_attempts'].format(total_attempts))
    if found_count > 0:
        print(texts['avg_attempts'].format(total_attempts//found_count))
        print(texts['total_time'].format(time.time() - start_time))

except Exception as e:
    print(f"\n{texts['program_error'].format(str(e))}")
    print(f"{texts['error_type'].format(type(e).__name__)}")
    print(texts['error_details'])
    import traceback
    traceback.print_exc()

finally:
    input(texts['press_enter'])