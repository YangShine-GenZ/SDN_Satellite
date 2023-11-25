import matplotlib.pyplot as plt
import numpy as np

size = 4
x = np.arange(size)


# 功能1
x_labels = ["1M", "10M", "50M", "100M"]
# 用第1组...替换横坐标x的值
plt.xticks(x, x_labels)
# 有a/b/c三种类型的数据，n设置为3
total_width, n = 0.8, 3
# 每种类型的柱状图宽度
width = total_width / n

# 重新设置x轴的坐标
x = x - (total_width - width) / 2
print(x)
# 返回size个0-1的随机数
a = np.random.random(size)
b = np.random.random(size)
c = np.random.random(size)

# 功能2
for i, j in zip(x, a):
    plt.text(i, j + 0.01, "%.2f" % j, ha="center", va="bottom", fontsize=7)
for i, j in zip(x + width, b):
    plt.text(i, j + 0.01, "%.2f" % j, ha="center", va="bottom", fontsize=7)
for i, j in zip(x + 2 * width, c):
    plt.text(i, j + 0.01, "%.2f" % j, ha="center", va="bottom", fontsize=7)


# 画柱状图
plt.bar(x, a, width=width, label="a")
plt.bar(x + width, b, width=width, label="b")
plt.bar(x + 2*width, c, width=width, label="c")
# 显示图例
plt.legend()
# 显示柱状图
plt.show()
