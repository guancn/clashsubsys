#!/usr/bin/env python3
"""
测试地区节点组正则模式匹配
"""
import re

def test_pattern_matching():
    """测试正则模式匹配"""
    print("测试地区节点组正则模式匹配")
    print("=" * 40)
    
    # 模拟节点列表
    test_nodes = [
        "🇭🇰 香港-01 [倍率:1.0]",
        "🇭🇰 香港-02 [倍率:1.0]", 
        "🇭🇰 HK-Premium-01",
        "🇨🇳 台湾-01 [倍率:1.0]",
        "🇨🇳 Taiwan-01",
        "🇸🇬 新加坡-01 [倍率:1.0]",
        "🇸🇬 Singapore-01", 
        "🇯🇵 日本-01 [倍率:1.0]",
        "🇯🇵 Japan-01",
        "🇺🇲 美国-01 [倍率:1.0]",
        "🇺🇲 USA-01",
        "🇺🇲 US-Premium-01"
    ]
    
    # 测试不同的地区匹配模式
    patterns = [
        ("香港|HK", "🇭🇰 香港节点"),
        ("台湾|Taiwan", "🇨🇳 台湾节点"),
        ("新加坡|Singapore", "🇸🇬 新加坡节点"),
        ("日本|Japan", "🇯🇵 日本节点"),
        ("美国|US|USA", "🇺🇲 美国节点")
    ]
    
    for pattern_str, group_name in patterns:
        print(f"\n测试 {group_name}:")
        print(f"  模式: .{pattern_str}.")
        
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = [node for node in test_nodes if pattern.search(node)]
            print(f"  匹配节点 ({len(matches)}): {matches}")
            
            if matches:
                print(f"  ✅ 成功匹配")
            else:
                print(f"  ❌ 无匹配节点")
                
        except re.error as e:
            print(f"  ❌ 正则错误: {e}")

def test_config_parsing():
    """测试配置解析"""
    print("\n\n测试配置字符串解析")
    print("=" * 30)
    
    config = "🇭🇰 香港节点`url-test`.香港|HK.`http://www.gstatic.com/generate_204`300,,50"
    print(f"配置字符串: {config}")
    
    parts = config.split('`')
    print(f"解析结果 ({len(parts)}部分):")
    for i, part in enumerate(parts):
        print(f"  parts[{i}]: '{part}'")
    
    if len(parts) >= 5:
        name = parts[0]
        group_type = parts[1]
        proxies_part = parts[2]
        url = parts[3]
        
        # 解析第4部分，格式可能是 "300,,50"
        interval_tolerance_part = parts[4]
        interval_parts = interval_tolerance_part.split(',')
        
        # 第一个是interval
        interval = int(interval_parts[0]) if interval_parts[0].isdigit() else 300
        
        # 最后一个非空部分是tolerance
        tolerance = 50
        for part in reversed(interval_parts):
            if part.strip() and part.strip().isdigit():
                tolerance = int(part.strip())
                break
        
        print(f"\n解析后的字段:")
        print(f"  名称: {name}")
        print(f"  类型: {group_type}")
        print(f"  代理规则: {proxies_part}")
        print(f"  测试URL: {url}")
        print(f"  间隔部分: '{interval_tolerance_part}'")
        print(f"    -> 间隔: {interval}")
        print(f"    -> 容差: {tolerance}")
        
        # 测试地区模式解析
        if proxies_part.startswith('.') and proxies_part.endswith('.'):
            pattern_str = proxies_part[1:-1]
            print(f"\n  地区模式: {pattern_str}")
            print(f"  ✅ 识别为地区匹配格式")
            
            # 测试节点匹配
            test_nodes = [
                "🇭🇰 香港-01 [倍率:1.0]",
                "🇭🇰 HK-Premium-01",
                "🇨🇳 台湾-01 [倍率:1.0]"
            ]
            
            import re
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                matches = [node for node in test_nodes if pattern.search(node)]
                print(f"  匹配节点: {matches}")
            except re.error as e:
                print(f"  正则错误: {e}")
        else:
            print(f"\n  ❌ 不是地区匹配格式")

if __name__ == "__main__":
    test_pattern_matching()
    test_config_parsing()