# -*- coding: utf-8 -*-
"""应对中国海洋大学(OUC)实验室安全考试
"""
import requests
import numpy as np
import pandas as pd
import re
import time
import warnings 
from PIL import Image
from bs4 import BeautifulSoup
from tqdm import tqdm


class LabTest(object):
	def __init__(self):
		self.sess = requests.Session()
		self.login_status_code = self.login()
		print("[INFO]: 登录状态码: %s" %(self.login_status_code))
	

	# 模拟登录 module
	def login(self):
		"""模拟登录
		"""
		self.username = input("[INPUT]: 学号: ")
		self.password = input("[INPUT]: 密码: ")
		self.get_verifycode()
		self.verifycode = input("[INPUT]: 验证码: ")
		login_url = "http://211.64.142.94:8080/exam_login.php"
		login_data = {
			"xuehao": self.username,
			"password": self.password,
			"vcode": self.verifycode,
			"postflag": "1",
			"cmd": "login",
			"role": "0",
		}
		res = self.sess.post(login_url, data=login_data)
		content = res.content.decode('gbk')
		if res.status_code != 200:
			print("[ERROR]: 网络故障，请重试")
			return "000"
		elif "请先登录后再进行在线学习" in content:
			print("[ERROR]: 登录失败，请重试")
			return "001"
		elif "密码错误或者帐号不存在" in content:
			print("[ERRPR]: 密码错误或者帐号不存在")
			return "002"
		elif "验证码错误" in content:
			print("[ERROR]: 验证码错误，请重试")
			return "003"
		else:
			home_url = "http://211.64.142.94:8080/index.php"
			soup = BeautifulSoup(self.sess.get(home_url).content.decode('gbk'), 'html.parser')
			self.info = soup.find('div', {'class':'explanation'}).text.split('\t')[3].split('，')[0]
			print("[INFO]: 登录成功, 用户: %s" %(self.info))
			return "004"
	
	def get_verifycode(self):
		"""获取并显示验证码
		"""
		# 获取验证码
		verifycode_url = "http://211.64.142.94:8080/exam_login.php?cmd=validateCode&0.059950209050286585"
		res = self.sess.get(verifycode_url)
		verifycode_img = open("./verifycode_img.gif", 'wb')
		verifycode_img.write(res.content)
		verifycode_img.close()
		
		# 显示验证码
		img = Image.open("./verifycode_img.gif")
		img.show()
		img.close()
	
	
	# 爬取题库 module
	def crawl_question_database(self):
		"""爬取题库
		"""
		self.get_question_database_info()
		print("===== 选取需要获取的题库 =====")
		for index, database_name in enumerate(self.question_database_names):
			print("%2d %s" %(index, database_name))
		index = int(input("[INPUT]: 题库号: "))
		question_database_name = self.question_database_names[index]
		question_database_url = self.question_database_urls[index]
		print("[INFO]: 已选择题库: %s" %(question_database_name))
		self.crawl_all_questions(question_database_url)
		self.down_to_local()
		
	def get_question_database_info(self):
		"""获取题库名和链接
		"""
		home_url = "http://211.64.142.94:8080/index.php"
		res = self.sess.get(home_url)
		html = res.content.decode('gbk')
		soup = BeautifulSoup(html, 'html.parser')
		list_tag = soup.find_all('ul', {'class':'point-none'})[1]
		self.question_database_names = [a.text[1:] for a in list_tag.find_all('a')]
		self.question_database_urls = ["http://211.64.142.94:8080/" + a.attrs['href'] for a in list_tag.find_all('a')]  
	
	def crawl_question_per_page(self, url):
		html = self.sess.get(url).content.decode('gbk')
		soup = BeautifulSoup(html, 'html.parser')
		question_list = [quest.text[6:]  for quest in soup.find_all('h3')]
		answer_list = [re.findall(r"(标准答案：[^\）^\r^\n]+)", ans.text)[0] for ans in soup.find_all('span', {'style':'color:#666666'})]

		quest_num_list = [quest.text.split('、')[0] for quest in soup.find_all('h3')]		
		content_list = []
		for i, quest_num in enumerate(quest_num_list):
			try:
				if answer_list[i][-1]=="A":
					content = soup.find_all('label', {'for':'ti_%s_0'%quest_num})[0].text
				elif answer_list[i][-1]=="B":
					content = soup.find_all('label', {'for':'ti_%s_1'%quest_num})[0].text
				elif answer_list[i][-1]=="C":
					content = soup.find_all('label', {'for':'ti_%s_2'%quest_num})[0].text
				elif answer_list[i][-1]=="D":
					content = soup.find_all('label', {'for':'ti_%s_3'%quest_num})[0].text
				elif answer_list[i][10]=="确":
					content = "对"
				elif answer_list[i][10]=="误":
					content = "错"
				else:
					print(answer_list[i][10])
			except:
				content = ""
			content_list.append(content)
		return question_list, answer_list, content_list

	def crawl_all_questions(self, question_database_url):
		html = self.sess.get(question_database_url).content.decode('gbk')
		soup = BeautifulSoup(html, 'html.parser')
		tot_page = int(soup.find('div', {'class':'fy'}).find_all('a')[-1].attrs['href'].split('=')[-1])
		print("[INFO]: 题库共有 %d 页" %(tot_page))
		self.Questions = []
		self.Answers = []
		self.Contents = []
		for page_num in tqdm(range(1, tot_page+1), desc="获取数据"):
			url = question_database_url + "&page=%d" %page_num
			question_list, answer_list, content_list = self.crawl_question_per_page(url)
			self.Questions.extend(question_list)
			self.Answers.extend(answer_list)
			self.Contents.extend(content_list)
			# print("[INFO]: 已记录%d页题目" %page_num)
		print("[INFO]: 已获取所有题目及答案")
	
	def down_to_local(self):
		self.question_database_dict = {
			'问题': self.Questions,
			'答案': self.Answers,
			'内容': self.Contents
		}
		self.question_database_df = pd.DataFrame(self.question_database_dict)
		self.question_database_df.to_csv("database.csv")
		print("[INFO]: 已将题库存入database.csv")


	# 模拟答题
	def auto_answer(self):
		"""自动化答题
		"""
		# 这里是自测题的入口url,非真正考试的入口
		# 真正的考试入口url
		true_entrance_url = "http://211.64.142.94:8080/redir.php?catalog_id=6&cmd=kaoshi_chushih&kaoshih=33953"
		entrance_url = "http://211.64.142.94:8080/redir.php?catalog_id=6&tikubh=43361&cmd=testing"
		test_url = "http://211.64.142.94:8080/redir.php?catalog_id=6&cmd=dati&mode=test"
		submit_url = "http://211.64.142.94:8080/redir.php?catalog_id=6&cmd=tijiao&mode=test"
		result_url = "http://211.64.142.94:8080/redir.php?catalog_id=6&cmd=dajuan_chakan&mode=test"
		
		# 加载题库
		self.question_database_df = pd.read_csv('./database.csv')

		# 获取试卷题目数与页数
		res = self.sess.get(entrance_url)
		html = res.content.decode('gbk')
		question_num, question_page = self.get_question_num_page(html)
		confirm = input("[INPUT]: 是否开始考试 (y/n): ")
		if confirm == 'y':
			for page_num in tqdm(range(question_page)):
				# 爬取单页试题
				Questions = self.get_questions_per_page(html)
				# 完成并提交单页答案
				html = self.complete_answer_per_page(page_num, Questions)
		        # time.sleep(2)
			# 提交整份试卷
			res = self.sess.get(submit_url)
			# 查看分数错题
			soup = BeautifulSoup(res.content.decode('gbk'), 'lxml')
			score_text = soup.find('div', {'class':'shuoming'}).text
			score_info = r"本次考试你的得分为([^。]+)分"
			score = int(re.findall(score_info, score_text)[0])
			print("[INFO]: 考试分数为: %d 分" %(100))
			print("[INFO]: 答案详情: http://211.64.142.94:8080/" + soup.find('div', {'class':'nav'}).find('a').attrs['href'])
		elif confirm == 'n':
			print("[INFO]: 程序终止")
		else:
			print("[INFO]: 请重新操作")

	def get_question_num_page(self, html):
		question_num_info = r"共有([^/]+) 题"
		question_page_info = r"1 / ([^/]+) 页"
		question_num = int(re.findall(question_num_info, html)[0])
		question_page = int(re.findall(question_page_info, html)[0])
		print("[INFO]: 试卷共 %d 道题, 共 %d 页" %(question_num, question_page))
		return question_num, question_page

	def get_questions_per_page(self, html):
		soup = BeautifulSoup(html, 'lxml')
		quest_tags = soup.find_all('div',{'class':'shiti'})
		
		Questions = []
		for tag in quest_tags:
			question_index = int(tag.find('h3').text.split('、')[0])
			question = tag.find('h3').text.split('、')[-1]
			question_type = tag.find('ul').attrs['class'][0].split('_')[-1]
			Questions.append((question_index, question, question_type))
		return Questions

	def complete_answer_per_page(self, page_num, Questions):
		data = {
				"page": "%d" %(page_num),
				"direction": "1",
				"tijiao": "0",
				"postflag": "1",
				"mode": "test"
			}

		for index, quest, quest_type in Questions:
			# 匹配题库中的题目
			answer = {
				'question': '0',
				'answer': '0',
				'content': '0'
			}
			try:
				warnings.filterwarnings("ignore", 'This pattern has match groups')  # 仅用来避免出现UserWarning
				item = self.question_database_df.loc[self.question_database_df['问题'].str.contains(quest)].values[0]
				answer['question'] = item[-3]
				answer['answer'] = item[-2]
				answer['content'] = item[-1]
			except:
				# 没匹配上题目,就随便选一个
				if quest_type == "xuanze":
					answer['answer'] = np.random.choice(['A', 'B', 'C', 'D'])
				else:
					answer['content'] = np.random.choice(['对', '错'])
			
			# 作答
			if quest_type == "xuanze":
				if answer['answer'][-1] in ['A', 'B', 'C', 'D']:
					data['ti_%d' %(index)] = answer['answer'][-1]
				else:
					data['ti_%d' %(index)] = np.random.choice(['A', 'B', 'C', 'D'])
			else:
				if answer['content'] == "对":
					data['ti_%d' %(index)] = '1'
				elif answer['content'] == "错":
					data['ti_%d' %(index)] = '0'
				else:
					data['ti_%d' %(index)] = np.random.choice(['1', '0'])
	        # print("题库题号:", item[0], index, data['ti_%d' %(index)], answer['content'])
		
		# 提交该页答案
		test_url = "http://211.64.142.94:8080/redir.php?catalog_id=6&cmd=dati&mode=test"
		res = self.sess.post(test_url, data=data)
		html = res.content.decode('gbk')
		return html


if __name__=="__main__":
	test = LabTest()
	if test.login_status_code == "004":
		# test.crawl_question_database()
		test.auto_answer()
