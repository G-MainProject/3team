package com.team3.backendapi.service.sns;

import com.team3.backendapi.dto.sns.SnsPostDto;
import com.team3.backendapi.dto.sns.SnsResponseDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class SnsService {

    private final RedditApiService redditApiService;

    private static final Map<String, String> STOCK_NAMES = new HashMap<>();
    
    static {
        STOCK_NAMES.put("005930", "삼성전자");
        STOCK_NAMES.put("000660", "SK하이닉스");
        STOCK_NAMES.put("035420", "NAVER");
        STOCK_NAMES.put("207940", "삼성바이오로직스");
        STOCK_NAMES.put("006400", "삼성SDI");
    }

    public Mono<SnsResponseDto> getSnsData(String symbol) {
        String stockName = STOCK_NAMES.getOrDefault(symbol, "알 수 없는 주식");
        
        log.info("SNS 데이터 요청 시작: {} ({})", stockName, symbol);

        // Reddit 데이터와 더미 Twitter 데이터를 가져오기
        Mono<List<SnsPostDto>> redditMono = redditApiService.getRedditPostsBySymbol(symbol, stockName)
                .doOnNext(redditPosts -> log.info("Reddit 데이터 수집 완료: {}개", redditPosts.size()))
                .doOnError(error -> log.error("Reddit 데이터 수집 실패: {}", error.getMessage()));

        // 더미 Twitter 데이터 생성
        List<SnsPostDto> dummyTweets = getDummyTweets(symbol, stockName);

        return redditMono
                .map(redditPosts -> {
                    log.info("SNS 데이터 조합 중: tweets={}개, reddit={}개", 
                        dummyTweets.size(), redditPosts.size());
                    return new SnsResponseDto(dummyTweets, redditPosts, stockName, symbol);
                })
                .doOnSuccess(response -> 
                    log.info("SNS 데이터 로드 완료: {} - Twitter: {}개, Reddit: {}개", 
                        stockName, response.getTweets().size(), response.getRedditPosts().size()))
                .doOnError(error -> 
                    log.error("SNS 데이터 로드 실패: {} - {}", symbol, error.getMessage()));
    }

    private List<SnsPostDto> getDummyTweets(String symbol, String stockName) {
        List<SnsPostDto> tweets = new ArrayList<>();
        
        // 심볼별 더미 데이터 생성 (10개씩)
        switch (symbol) {
            case "005930":
                tweets.add(new SnsPostDto("1", "@SamsungNews", 
                    "삼성전자, 3분기 실적 발표로 AI 반도체 수요 증가에 따른 긍정적 전망을 제시했습니다. 특히 HBM3E 메모리 기술의 상용화로 데이터센터 시장에서의 경쟁력이 크게 향상될 것으로 예상됩니다. 글로벌 AI 서버 수요 급증과 맞물려 향후 2-3년간 지속적인 성장이 기대되는 상황입니다.", 
                    "2시간 전", 1240, 89, 0, "twitter", "https://twitter.com/SamsungNews/status/1234567890"));
                tweets.add(new SnsPostDto("2", "@TechAnalyst", 
                    "삼성전자 메모리 반도체 기술력이 업계를 선도하고 있다. 특히 HBM 기술에서 SK하이닉스와의 치열한 경쟁이 벌어지고 있는데, 삼성전자의 차세대 HBM4 기술 개발이 순조롭게 진행되고 있어 향후 시장 점유율 확대가 예상됩니다. 또한 파운드리 사업에서도 TSMC와의 격차를 줄여나가고 있어 종합적인 반도체 생태계 구축에 성공하고 있습니다.", 
                    "4시간 전", 892, 156, 0, "twitter", "https://twitter.com/TechAnalyst/status/1234567891"));
                tweets.add(new SnsPostDto("3", "@InvestorDaily", 
                    "삼성전자 주가 상승세가 지속되고 있습니다. 글로벌 공급망 안정화와 AI 수요 증가가 주요 견인 요인으로 작용하고 있으며, 특히 중국 시장 복구와 미국 데이터센터 투자 확대로 인한 메모리 반도체 수요 급증이 긍정적으로 작용하고 있습니다. 또한 자율주행 반도체와 IoT 디바이스용 반도체 수요도 함께 증가하고 있어 다각화된 성장 동력을 확보하고 있습니다.", 
                    "6시간 전", 2103, 234, 0, "twitter", "https://twitter.com/InvestorDaily/status/1234567892"));
                tweets.add(new SnsPostDto("4", "@MemoryExpert", 
                    "삼성전자의 차세대 메모리 기술이 업계 표준을 이끌고 있다. 특히 DDR5와 HBM3 기술에서의 우위를 바탕으로 데이터센터, AI 서버, 게임 콘솔 등 다양한 분야에서의 수요 증가를 견인하고 있습니다. 또한 3D NAND 플래시 메모리 기술에서도 경쟁사 대비 우수한 성능과 안정성을 보여주고 있어 스마트폰과 SSD 시장에서의 경쟁력도 지속적으로 강화되고 있습니다.", 
                    "8시간 전", 1567, 123, 0, "twitter", "https://twitter.com/MemoryExpert/status/1234567893"));
                tweets.add(new SnsPostDto("5", "@StockMarket", 
                    "삼성전자가 반도체 업사이클 진입으로 수익성 개선이 기대되고 있습니다. 메모리 반도체 가격 상승과 함께 파운드리 사업의 수주 증가로 인한 수익성 개선이 예상되며, 특히 고부가가치 제품 비중 확대와 생산 효율성 향상으로 인한 마진 개선이 주목받고 있습니다. 또한 ESG 경영 강화를 통한 지속가능한 성장 모델 구축도 투자 매력도를 높이는 요인으로 작용하고 있습니다.", 
                    "10시간 전", 934, 67, 0, "twitter", "https://twitter.com/StockMarket/status/1234567894"));
                tweets.add(new SnsPostDto("6", "@TechNews", 
                    "삼성전자 파운드리 사업 확장으로 글로벌 시장 점유율을 확대하고 있습니다. 3나노미터 이하 초미세 공정 기술 개발에 성공하여 TSMC와의 기술 격차를 줄여나가고 있으며, 특히 고객사 다변화를 통해 리스크를 분산시키고 있습니다. 또한 자동차 반도체와 IoT 반도체 시장 진출을 통해 새로운 성장 동력을 확보하고 있어 장기적인 관점에서 투자 가치가 높아지고 있습니다.", 
                    "12시간 전", 1456, 98, 0, "twitter", "https://twitter.com/TechNews/status/1234567895"));
                tweets.add(new SnsPostDto("7", "@FinanceExpert", 
                    "삼성전자가 AI 반도체 투자를 확대하여 미래 성장 동력을 확보하고 있습니다. 특히 뉴럴 프로세싱 유닛(NPU)과 AI 가속기 개발에 집중하고 있으며, 데이터센터용 AI 칩 개발을 통해 클라우드 서비스 업체들과의 협력을 강화하고 있습니다. 또한 엣지 AI와 온디바이스 AI 기술 개발을 통해 스마트폰과 IoT 디바이스 시장에서의 경쟁 우위를 확보하려는 전략을 추진하고 있습니다.", 
                    "14시간 전", 789, 45, 0, "twitter", "https://twitter.com/FinanceExpert/status/1234567896"));
                tweets.add(new SnsPostDto("8", "@MarketWatch", 
                    "삼성전자 주가 분석 결과 현재 수준에서 매수 기회가 있다고 판단됩니다. 기술적 분석상 주요 지지선을 유지하고 있으며, 펀더멘털 분석에서도 반도체 업사이클 진입과 AI 수요 증가로 인한 수익성 개선이 예상되어 목표주가 상향 조정이 이루어지고 있습니다. 또한 배당 수익률과 PER 관점에서도 합리적인 수준을 유지하고 있어 중장기 투자 관점에서 매력적인 종목으로 평가받고 있습니다.", 
                    "16시간 전", 1234, 78, 0, "twitter", "https://twitter.com/MarketWatch/status/1234567897"));
                tweets.add(new SnsPostDto("9", "@TechInvestor", 
                    "삼성전자가 자율주행 반도체 기술 혁신을 통해 자동차 시장에 진출하고 있습니다. ADAS(고급운전자보조시스템)용 반도체와 자율주행 AI 칩 개발에 성공하여 글로벌 자동차 제조사들과의 협력을 확대하고 있습니다. 특히 전기차 시장의 급성장과 맞물려 자동차 반도체 수요가 급증하고 있어 새로운 성장 동력으로 기대되고 있습니다. 또한 자동차용 디스플레이와 배터리 관리 시스템 사업도 함께 확장하고 있습니다.", 
                    "18시간 전", 2100, 189, 0, "twitter", "https://twitter.com/TechInvestor/status/1234567898"));
                tweets.add(new SnsPostDto("10", "@StockAnalyst", 
                    "삼성전자가 ESG 경영을 강화하여 지속가능한 성장 모델을 구축하고 있습니다. 탄소 중립 목표 달성을 위한 친환경 제조 공정 도입과 재생에너지 사용 확대를 추진하고 있으며, 사회적 가치 창출을 위한 다양한 프로그램을 운영하고 있습니다. 또한 지배구조 개선과 투명한 경영을 통해 기업 가치를 높이고 있으며, 이러한 노력들이 장기적인 투자 매력도 향상으로 이어지고 있습니다.", 
                    "20시간 전", 500, 50, 0, "twitter", "https://twitter.com/StockAnalyst/status/1234567899"));
                break;
            case "000660":
                tweets.add(new SnsPostDto("1", "@SKHynixNews", 
                    "SK하이닉스가 HBM3E 메모리 대량 생산을 시작하여 AI 서버 수요 급증에 대응하고 있습니다. 특히 엔비디아와의 전략적 파트너십을 통해 데이터센터용 고성능 메모리 공급을 확대하고 있으며, 차세대 HBM4 기술 개발에도 박차를 가하고 있습니다. 글로벌 AI 서버 시장의 폭발적 성장과 맞물려 향후 3년간 연평균 30% 이상의 성장이 예상되는 상황입니다.", 
                    "1시간 전", 1567, 123, 0, "twitter", "https://twitter.com/SKHynixNews/status/2234567890"));
                tweets.add(new SnsPostDto("2", "@MemoryTech", 
                    "SK하이닉스의 차세대 메모리 기술이 업계 표준을 이끌고 있습니다. 특히 DDR5와 LPDDR5 기술에서의 우위를 바탕으로 스마트폰, 노트북, 서버 등 다양한 분야에서의 수요 증가를 견인하고 있으며, 3D NAND 플래시 메모리 기술에서도 경쟁사 대비 우수한 성능과 안정성을 보여주고 있습니다. 또한 자동차용 메모리 반도체 시장 진출을 통해 새로운 성장 동력을 확보하고 있습니다.", 
                    "3시간 전", 934, 67, 0, "twitter", "https://twitter.com/MemoryTech/status/2234567891"));
                tweets.add(new SnsPostDto("3", "@TechExpert", 
                    "SK하이닉스가 AI 메모리 시장에서 삼성전자와 치열한 경쟁을 벌이고 있습니다. HBM 기술에서의 경쟁력 강화를 위해 대규모 R&D 투자를 진행하고 있으며, 특히 AI 서버용 고대역폭 메모리 개발에 집중하고 있습니다. 또한 파트너사들과의 협력을 통해 생태계 구축에도 힘쓰고 있어 장기적인 경쟁 우위 확보에 주력하고 있습니다.", 
                    "5시간 전", 2103, 234, 0, "twitter", "https://twitter.com/TechExpert/status/2234567892"));
                tweets.add(new SnsPostDto("4", "@InvestorNews", 
                    "SK하이닉스 주가 전망이 긍정적으로 전환되고 있습니다. 메모리 업사이클 진입과 AI 수요 증가로 인한 수익성 개선이 예상되며, 특히 고부가가치 제품 비중 확대와 생산 효율성 향상으로 인한 마진 개선이 주목받고 있습니다. 또한 중국 시장 복구와 미국 데이터센터 투자 확대로 인한 수요 증가도 긍정적으로 작용하고 있습니다.", 
                    "7시간 전", 1240, 89, 0, "twitter", "https://twitter.com/InvestorNews/status/2234567893"));
                tweets.add(new SnsPostDto("5", "@MarketAnalysis", 
                    "SK하이닉스가 중국 시장 복구로 수출 증가가 기대되고 있습니다. 중국 정부의 반도체 산업 지원 정책과 함께 국내 스마트폰 제조사들의 수요 증가가 긍정적으로 작용하고 있으며, 특히 5G 스마트폰용 메모리 반도체 수요가 크게 증가하고 있습니다. 또한 중국 데이터센터 시장의 성장과 맞물려 서버용 메모리 수요도 함께 증가하고 있습니다.", 
                    "9시간 전", 892, 156, 0, "twitter", "https://twitter.com/MarketAnalysis/status/2234567894"));
                tweets.add(new SnsPostDto("6", "@TechTrends", 
                    "SK하이닉스가 차세대 메모리 기술 개발을 통해 경쟁 우위를 확보하고 있습니다. 특히 AI와 머신러닝 워크로드에 최적화된 메모리 아키텍처 개발에 집중하고 있으며, 엣지 컴퓨팅과 클라우드 컴퓨팅 환경에서의 성능 향상을 위한 다양한 기술 혁신을 추진하고 있습니다. 또한 자동차용 메모리 반도체 시장 진출을 통해 새로운 성장 동력을 확보하고 있습니다.", 
                    "11시간 전", 1456, 98, 0, "twitter", "https://twitter.com/TechTrends/status/2234567895"));
                tweets.add(new SnsPostDto("7", "@FinanceUpdate", 
                    "SK하이닉스가 ESG 경영을 강화하여 투자 매력도를 높이고 있습니다. 탄소 중립 목표 달성을 위한 친환경 제조 공정 도입과 재생에너지 사용 확대를 추진하고 있으며, 사회적 가치 창출을 위한 다양한 프로그램을 운영하고 있습니다. 또한 지배구조 개선과 투명한 경영을 통해 기업 가치를 높이고 있으며, 이러한 노력들이 장기적인 투자 매력도 향상으로 이어지고 있습니다.", 
                    "13시간 전", 789, 45, 0, "twitter", "https://twitter.com/FinanceUpdate/status/2234567896"));
                tweets.add(new SnsPostDto("8", "@StockInsight", 
                    "SK하이닉스가 AI 데이터센터 수요 증가로 성장 동력을 확보하고 있습니다. 특히 클라우드 서비스 업체들과의 전략적 파트너십을 통해 고성능 메모리 공급을 확대하고 있으며, AI 훈련과 추론에 최적화된 메모리 솔루션 개발에 집중하고 있습니다. 또한 엣지 AI와 온디바이스 AI 기술 발전에 따른 새로운 메모리 수요 창출에도 주력하고 있습니다.", 
                    "15시간 전", 1234, 78, 0, "twitter", "https://twitter.com/StockInsight/status/2234567897"));
                tweets.add(new SnsPostDto("9", "@TechReview", 
                    "SK하이닉스가 메모리 반도체 기술 혁신을 통해 글로벌 시장 점유율을 확대하고 있습니다. 특히 HBM 기술에서의 경쟁력 강화를 위해 대규모 R&D 투자를 진행하고 있으며, 차세대 메모리 아키텍처 개발에 집중하고 있습니다. 또한 파트너사들과의 협력을 통해 생태계 구축에도 힘쓰고 있어 장기적인 경쟁 우위 확보에 주력하고 있습니다.", 
                    "17시간 전", 2100, 189, 0, "twitter", "https://twitter.com/TechReview/status/2234567898"));
                tweets.add(new SnsPostDto("10", "@MarketNews", 
                    "SK하이닉스가 반도체 장비 투자를 확대하여 생산성을 향상시키고 있습니다. 특히 AI와 고성능 컴퓨팅용 메모리 생산을 위한 최신 장비 도입에 집중하고 있으며, 생산 효율성 향상과 품질 개선을 위한 자동화 시스템 구축에도 투자하고 있습니다. 또한 차세대 메모리 기술 개발을 위한 연구 시설 확충과 인력 확보에도 힘쓰고 있습니다.", 
                    "19시간 전", 500, 50, 0, "twitter", "https://twitter.com/MarketNews/status/2234567899"));
                break;
            case "035420":
                tweets.add(new SnsPostDto("1", "@NaverTech", 
                    "네이버가 AI 검색 기술 혁신을 통해 사용자 경험을 대폭 개선하고 있습니다. 특히 자연어 처리 기술과 머신러닝 알고리즘을 활용한 지능형 검색 서비스를 도입하여 검색 정확도와 관련성을 크게 향상시켰습니다. 또한 개인화된 검색 결과 제공과 실시간 정보 업데이트 기능을 통해 사용자 만족도를 높이고 있으며, 이러한 기술 혁신이 검색 시장에서의 경쟁 우위를 강화하고 있습니다.", 
                    "2시간 전", 2100, 189, 0, "twitter", "https://twitter.com/NaverTech/status/3234567890"));
                tweets.add(new SnsPostDto("2", "@TechKorea", 
                    "네이버의 클라우드 서비스 확장으로 수익성 개선이 기대되고 있습니다. 특히 네이버 클라우드 플랫폼(NCP)의 글로벌 진출을 통해 해외 시장에서의 매출 증가를 견인하고 있으며, AI와 빅데이터 분석 서비스를 통한 고부가가치 클라우드 솔루션 제공에 집중하고 있습니다. 또한 중소기업과 스타트업을 대상으로 한 클라우드 마이그레이션 서비스 확대를 통해 시장 점유율을 높이고 있습니다.", 
                    "4시간 전", 1456, 98, 0, "twitter", "https://twitter.com/TechKorea/status/3234567891"));
                tweets.add(new SnsPostDto("3", "@ITNews", 
                    "네이버가 쇼핑몰 사업 성장을 통해 플랫폼 비즈니스를 강화하고 있습니다. 특히 스마트스토어와 네이버쇼핑을 통한 온라인 쇼핑 생태계 구축에 성공했으며, AI 기반 상품 추천 시스템과 개인화된 쇼핑 경험 제공으로 사용자 참여도를 높이고 있습니다. 또한 라이브 커머스와 소셜 커머스 기능 확대를 통해 새로운 쇼핑 트렌드에 대응하고 있습니다.", 
                    "6시간 전", 1234, 78, 0, "twitter", "https://twitter.com/ITNews/status/3234567892"));
                tweets.add(new SnsPostDto("4", "@DigitalTrends", 
                    "네이버가 AI 기술 투자를 확대하여 미래 성장 동력을 확보하고 있습니다. 특히 자연어 처리, 컴퓨터 비전, 음성 인식 등 핵심 AI 기술 개발에 집중하고 있으며, 이러한 기술들을 검색, 쇼핑, 클라우드 등 다양한 서비스에 적용하고 있습니다. 또한 AI 연구소 확충과 글로벌 AI 인재 확보를 통해 기술 경쟁력을 강화하고 있습니다.", 
                    "8시간 전", 2103, 234, 0, "twitter", "https://twitter.com/DigitalTrends/status/3234567893"));
                tweets.add(new SnsPostDto("5", "@TechInvestor", 
                    "네이버가 검색 시장에서의 경쟁력을 강화하여 시장 점유율을 유지하고 있습니다. 특히 구글과의 경쟁에서 차별화된 서비스를 제공하기 위해 한국어 검색 최적화와 로컬 콘텐츠 강화에 집중하고 있으며, 실시간 정보 제공과 개인화된 검색 결과를 통해 사용자 만족도를 높이고 있습니다. 또한 검색 광고 비즈니스의 수익성 개선을 통해 안정적인 수익 구조를 구축하고 있습니다.", 
                    "10시간 전", 1240, 89, 0, "twitter", "https://twitter.com/TechInvestor/status/3234567894"));
                tweets.add(new SnsPostDto("6", "@BusinessNews", 
                    "네이버가 글로벌 진출을 확대하여 해외 매출 증가를 기대하고 있습니다. 특히 일본과 동남아시아 시장을 중심으로 한 해외 진출을 통해 글로벌 사용자 확보에 집중하고 있으며, 현지화된 서비스 제공과 파트너십 구축을 통해 시장 점유율을 높이고 있습니다. 또한 글로벌 클라우드 서비스 제공을 통해 B2B 시장에서의 성장도 기대하고 있습니다.", 
                    "12시간 전", 892, 156, 0, "twitter", "https://twitter.com/BusinessNews/status/3234567895"));
                tweets.add(new SnsPostDto("7", "@InnovationHub", 
                    "네이버가 핀테크 사업을 확장하여 금융 서비스 영역에 진출하고 있습니다. 특히 네이버페이를 통한 간편결제 서비스 확대와 금융 상품 비교 서비스 제공을 통해 금융 생태계 구축에 집중하고 있으며, AI 기반 금융 상담 서비스와 개인화된 금융 솔루션 개발에도 힘쓰고 있습니다. 또한 금융권과의 파트너십을 통해 새로운 금융 서비스 모델을 창출하고 있습니다.", 
                    "14시간 전", 789, 45, 0, "twitter", "https://twitter.com/InnovationHub/status/3234567896"));
                tweets.add(new SnsPostDto("8", "@TechAnalysis", 
                    "네이버가 모바일 플랫폼을 강화하여 사용자 참여도를 증가시키고 있습니다. 특히 모바일 앱의 사용자 경험 개선과 개인화된 콘텐츠 제공을 통해 사용자 이탈률을 줄이고 있으며, 모바일 광고 비즈니스의 성장을 통해 수익성을 높이고 있습니다. 또한 모바일 결제와 모바일 쇼핑 서비스 통합을 통해 원스톱 모바일 플랫폼 구축에 집중하고 있습니다.", 
                    "16시간 전", 1567, 123, 0, "twitter", "https://twitter.com/TechAnalysis/status/3234567897"));
                tweets.add(new SnsPostDto("9", "@DigitalFuture", 
                    "네이버가 메타버스 기술 개발을 통해 새로운 비즈니스 모델을 구축하고 있습니다. 특히 ZEPETO 플랫폼을 통한 가상 세계 서비스 제공과 NFT 및 블록체인 기술 활용을 통해 메타버스 생태계 구축에 집중하고 있으며, 가상 현실과 증강 현실 기술 개발에도 투자하고 있습니다. 또한 메타버스 내에서의 새로운 광고 모델과 커머스 서비스 개발을 통해 수익화 방안을 모색하고 있습니다.", 
                    "18시간 전", 934, 67, 0, "twitter", "https://twitter.com/DigitalFuture/status/3234567898"));
                tweets.add(new SnsPostDto("10", "@TechUpdate", 
                    "네이버가 데이터 중심 경영을 통해 의사결정 정확도를 향상시키고 있습니다. 특히 빅데이터 분석과 AI를 활용한 실시간 비즈니스 인사이트 제공을 통해 경영진의 의사결정을 지원하고 있으며, 사용자 행동 데이터 분석을 통한 서비스 개선과 신규 서비스 개발에 집중하고 있습니다. 또한 데이터 기반의 마케팅 전략 수립과 고객 세분화를 통해 마케팅 효율성을 높이고 있습니다.", 
                    "20시간 전", 500, 50, 0, "twitter", "https://twitter.com/TechUpdate/status/3234567899"));
                break;
            case "207940":
                tweets.add(new SnsPostDto("1", "@BioTechNews", 
                    "삼성바이오로직스가 신약 개발 파트너십을 확대하여 성장 동력을 확보하고 있습니다. 특히 글로벌 제약사들과의 전략적 협력을 통해 바이오시밀러와 바이오베터 개발에 집중하고 있으며, CDMO(위탁개발생산) 사업 확장을 통해 수익성 개선을 도모하고 있습니다. 또한 차세대 바이오의약품 기술 개발을 통해 경쟁 우위를 확보하고 있으며, 이러한 노력들이 장기적인 성장 동력으로 작용하고 있습니다.", 
                    "1시간 전", 789, 45, 0, "twitter", "https://twitter.com/BioTechNews/status/4234567890"));
                tweets.add(new SnsPostDto("2", "@PharmaExpert", 
                    "삼성바이오로직스가 바이오시밀러 기술력을 바탕으로 글로벌 시장에 진출하고 있습니다. 특히 항체 의약품과 단백질 의약품 분야에서의 기술력 인정을 받아 유럽과 미국 시장에서의 점유율을 확대하고 있으며, 품질과 안정성에서 경쟁사 대비 우수한 성능을 보여주고 있습니다. 또한 신규 바이오시밀러 품목 개발을 통해 제품 포트폴리오를 다양화하고 있습니다.", 
                    "3시간 전", 1234, 78, 0, "twitter", "https://twitter.com/PharmaExpert/status/4234567891"));
                tweets.add(new SnsPostDto("3", "@BioInvestor", 
                    "삼성바이오로직스가 CDMO 사업 확장을 통해 수익성을 개선하고 있습니다. 특히 글로벌 제약사들의 바이오의약품 개발 수요 증가에 대응하여 생산 시설을 확충하고 있으며, 고부가가치 제품 생산 비중을 높여 마진을 개선하고 있습니다. 또한 신규 고객사 확보와 기존 고객사와의 장기 계약 체결을 통해 안정적인 수익 구조를 구축하고 있습니다.", 
                    "5시간 전", 2103, 234, 0, "twitter", "https://twitter.com/BioInvestor/status/4234567892"));
                tweets.add(new SnsPostDto("4", "@HealthTech", 
                    "삼성바이오로직스가 AI 기반 신약 개발 플랫폼을 구축하고 있습니다. 특히 머신러닝과 딥러닝 기술을 활용한 약물 발견과 개발 과정의 효율성을 높이고 있으며, 디지털 트윈 기술을 통한 생산 공정 최적화에도 집중하고 있습니다. 또한 AI 기반의 품질 관리 시스템 도입을 통해 제품 품질을 향상시키고 있으며, 이러한 기술 혁신이 경쟁 우위 강화에 기여하고 있습니다.", 
                    "7시간 전", 1240, 89, 0, "twitter", "https://twitter.com/HealthTech/status/4234567893"));
                tweets.add(new SnsPostDto("5", "@BioAnalysis", 
                    "삼성바이오로직스가 글로벌 제약사들과의 협력을 확대하여 성장하고 있습니다. 특히 대형 제약사들과의 전략적 파트너십을 통해 바이오의약품 개발과 생산에 참여하고 있으며, 신규 치료 영역 확장을 통한 시장 기회를 모색하고 있습니다. 또한 제약사들의 아웃소싱 수요 증가에 대응하여 CDMO 서비스 범위를 확대하고 있으며, 이러한 협력이 수익성 개선에 기여하고 있습니다.", 
                    "9시간 전", 892, 156, 0, "twitter", "https://twitter.com/BioAnalysis/status/4234567894"));
                tweets.add(new SnsPostDto("6", "@PharmaNews", 
                    "삼성바이오로직스가 바이오의약품 생산 기술을 혁신하고 있습니다. 특히 연속 제조 공정 도입을 통해 생산 효율성을 높이고 있으며, 자동화 시스템 구축을 통해 품질 일관성을 향상시키고 있습니다. 또한 친환경 생산 공정 개발을 통해 ESG 경영을 강화하고 있으며, 이러한 기술 혁신이 생산성 향상과 비용 절감에 기여하고 있습니다.", 
                    "11시간 전", 1456, 98, 0, "twitter", "https://twitter.com/PharmaNews/status/4234567895"));
                tweets.add(new SnsPostDto("7", "@BioTechTrends", 
                    "삼성바이오로직스가 ESG 경영을 강화하여 지속가능한 성장을 추진하고 있습니다. 특히 탄소 중립 목표 달성을 위한 친환경 생산 공정 도입과 재생에너지 사용 확대를 추진하고 있으며, 사회적 가치 창출을 위한 다양한 프로그램을 운영하고 있습니다. 또한 지배구조 개선과 투명한 경영을 통해 기업 가치를 높이고 있으며, 이러한 노력들이 장기적인 투자 매력도 향상으로 이어지고 있습니다.", 
                    "13시간 전", 789, 45, 0, "twitter", "https://twitter.com/BioTechTrends/status/4234567896"));
                tweets.add(new SnsPostDto("8", "@HealthInvestor", 
                    "삼성바이오로직스가 신약 파이프라인을 확대하여 미래 성장성을 확보하고 있습니다. 특히 자체 신약 개발과 파트너사와의 공동 개발을 통해 다양한 치료 영역에서의 제품 포트폴리오를 확장하고 있으며, 차세대 바이오의약품 기술 개발에 집중하고 있습니다. 또한 글로벌 임상시험 확대를 통해 해외 시장 진출을 가속화하고 있으며, 이러한 노력들이 장기적인 성장 동력으로 작용하고 있습니다.", 
                    "15시간 전", 1567, 123, 0, "twitter", "https://twitter.com/HealthInvestor/status/4234567897"));
                tweets.add(new SnsPostDto("9", "@BioInnovation", 
                    "삼성바이오로직스가 차세대 바이오 기술 개발을 통해 경쟁 우위를 확보하고 있습니다. 특히 세포 치료제와 유전자 치료제 분야에서의 기술 개발에 집중하고 있으며, mRNA 기술과 나노 기술을 활용한 새로운 치료법 개발에도 투자하고 있습니다. 또한 디지털 헬스케어와 연계된 바이오의약품 개발을 통해 미래 의료 시장 변화에 대응하고 있습니다.", 
                    "17시간 전", 934, 67, 0, "twitter", "https://twitter.com/BioInnovation/status/4234567898"));
                tweets.add(new SnsPostDto("10", "@PharmaUpdate", 
                    "삼성바이오로직스가 글로벌 시장 점유율을 확대하여 성장을 지속하고 있습니다. 특히 아시아 태평양 지역과 중동 지역에서의 시장 진출을 가속화하고 있으며, 현지화된 서비스 제공과 파트너십 구축을 통해 시장 점유율을 높이고 있습니다. 또한 글로벌 규제 환경 변화에 대응하여 다양한 인증을 취득하고 있으며, 이러한 노력들이 해외 시장에서의 경쟁력 강화에 기여하고 있습니다.", 
                    "19시간 전", 500, 50, 0, "twitter", "https://twitter.com/PharmaUpdate/status/4234567899"));
                break;
            case "006400":
                tweets.add(new SnsPostDto("1", "@BatteryTech", 
                    "삼성SDI가 전기차 배터리 기술 혁신을 통해 글로벌 시장 점유율을 확대하고 있습니다. 특히 고에너지 밀도 리튬이온 배터리 개발과 고속 충전 기술 혁신을 통해 전기차 성능을 향상시키고 있으며, 글로벌 자동차 제조사들과의 전략적 파트너십을 통해 시장 진출을 가속화하고 있습니다. 또한 차세대 배터리 기술인 솔리드 스테이트 배터리 개발에도 집중하고 있어 미래 시장에서의 경쟁 우위를 확보하고 있습니다.", 
                    "3시간 전", 1234, 78, 0, "twitter", "https://twitter.com/BatteryTech/status/5234567890"));
                tweets.add(new SnsPostDto("2", "@EVNews", 
                    "삼성SDI가 차세대 배터리 기술 개발을 통해 전기차 시장을 선도하고 있습니다. 특히 4680 원통형 배터리와 프리즘형 배터리 기술 개발에 성공하여 다양한 자동차 플랫폼에 적용할 수 있는 유연성을 확보했으며, 배터리 셀과 모듈, 팩까지 통합 솔루션을 제공하고 있습니다. 또한 배터리 수명 연장과 안전성 향상을 위한 기술 개발에도 집중하고 있어 시장 신뢰도를 높이고 있습니다.", 
                    "5시간 전", 2103, 234, 0, "twitter", "https://twitter.com/EVNews/status/5234567891"));
                tweets.add(new SnsPostDto("3", "@EnergyTech", 
                    "삼성SDI가 에너지 저장 시스템(ESS) 사업을 확대하여 성장 동력을 확보하고 있습니다. 특히 재생에너지 확산에 따른 에너지 저장 수요 증가에 대응하여 대용량 ESS 솔루션 개발에 집중하고 있으며, 상용 및 산업용 ESS 시장에서의 경쟁력을 강화하고 있습니다. 또한 가정용 ESS와 마이크로그리드 솔루션 개발을 통해 분산 에너지 시장에 진출하고 있으며, 이러한 노력들이 새로운 성장 동력으로 작용하고 있습니다.", 
                    "7시간 전", 1240, 89, 0, "twitter", "https://twitter.com/EnergyTech/status/5234567892"));
                tweets.add(new SnsPostDto("4", "@BatteryExpert", 
                    "삼성SDI가 고용량 배터리 기술 개발을 통해 전기차 주행거리를 연장하고 있습니다. 특히 실리콘 음극재와 고니켈 양극재 기술을 활용한 고에너지 밀도 배터리 개발에 성공했으며, 이를 통해 동일한 크기에서 더 긴 주행거리를 제공할 수 있게 되었습니다. 또한 배터리 관리 시스템(BMS) 기술 혁신을 통해 배터리 효율성을 극대화하고 있으며, 이러한 기술들이 전기차 시장에서의 경쟁 우위를 강화하고 있습니다.", 
                    "9시간 전", 892, 156, 0, "twitter", "https://twitter.com/BatteryExpert/status/5234567893"));
                tweets.add(new SnsPostDto("5", "@GreenTech", 
                    "삼성SDI가 친환경 배터리 기술 개발을 통해 ESG 경영을 강화하고 있습니다. 특히 코발트 사용량을 줄인 무코발트 배터리 기술 개발에 성공했으며, 재활용 가능한 소재 사용을 늘려 환경 친화적인 배터리 생산에 집중하고 있습니다. 또한 탄소 중립 목표 달성을 위한 친환경 생산 공정 도입과 재생에너지 사용 확대를 추진하고 있으며, 이러한 노력들이 지속가능한 성장 모델 구축에 기여하고 있습니다.", 
                    "11시간 전", 1456, 98, 0, "twitter", "https://twitter.com/GreenTech/status/5234567894"));
                tweets.add(new SnsPostDto("6", "@EVInvestor", 
                    "삼성SDI가 글로벌 자동차 제조사들과의 협력을 확대하여 성장하고 있습니다. 특히 테슬라, BMW, 포드 등 주요 자동차 제조사들과의 장기 공급 계약을 체결하여 안정적인 수익 구조를 구축했으며, 신규 자동차 제조사들과의 파트너십도 확대하고 있습니다. 또한 자동차 제조사들의 전기차 라인업 확대에 대응하여 생산 능력을 증설하고 있으며, 이러한 협력이 시장 점유율 확대에 기여하고 있습니다.", 
                    "13시간 전", 789, 45, 0, "twitter", "https://twitter.com/EVInvestor/status/5234567895"));
                tweets.add(new SnsPostDto("7", "@BatteryTrends", 
                    "삼성SDI가 배터리 안전성 기술 혁신을 통해 시장 신뢰도를 향상시키고 있습니다. 특히 배터리 화재 방지를 위한 다층 분리막 기술과 열 관리 시스템 개발에 성공했으며, 배터리 셀 레벨에서의 안전성 검증 시스템을 구축했습니다. 또한 AI 기반 배터리 상태 모니터링 시스템을 통해 실시간 안전성 관리가 가능하도록 했으며, 이러한 기술들이 시장에서의 경쟁 우위를 강화하고 있습니다.", 
                    "15시간 전", 1567, 123, 0, "twitter", "https://twitter.com/BatteryTrends/status/5234567896"));
                tweets.add(new SnsPostDto("8", "@EnergyFuture", 
                    "삼성SDI가 재생에너지 저장 솔루션을 통해 에너지 전환을 선도하고 있습니다. 특히 태양광과 풍력 발전과 연계된 대용량 ESS 솔루션 개발에 집중하고 있으며, 스마트 그리드와 연계된 에너지 관리 시스템 구축에도 힘쓰고 있습니다. 또한 수소 연료전지와 배터리를 결합한 하이브리드 에너지 저장 시스템 개발을 통해 미래 에너지 시장 변화에 대응하고 있습니다.", 
                    "17시간 전", 934, 67, 0, "twitter", "https://twitter.com/EnergyFuture/status/5234567897"));
                tweets.add(new SnsPostDto("9", "@TechInnovation", 
                    "삼성SDI가 AI 기반 배터리 관리 시스템을 통해 효율성을 극대화하고 있습니다. 특히 머신러닝 알고리즘을 활용한 배터리 수명 예측과 충전 최적화 기술 개발에 성공했으며, 실시간 배터리 상태 모니터링과 예방적 유지보수가 가능한 시스템을 구축했습니다. 또한 디지털 트윈 기술을 활용한 배터리 설계 최적화와 성능 시뮬레이션을 통해 개발 효율성을 높이고 있으며, 이러한 기술 혁신이 경쟁 우위 강화에 기여하고 있습니다.", 
                    "19시간 전", 2100, 189, 0, "twitter", "https://twitter.com/TechInnovation/status/5234567898"));
                tweets.add(new SnsPostDto("10", "@BatteryUpdate", 
                    "삼성SDI가 글로벌 배터리 시장에서의 경쟁력을 강화하고 있습니다. 특히 중국과 유럽 시장에서의 생산 시설 확충을 통해 현지화 전략을 추진하고 있으며, 현지 자동차 제조사들과의 파트너십 구축을 통해 시장 진출을 가속화하고 있습니다. 또한 배터리 재활용 사업 진출을 통해 순환 경제 모델을 구축하고 있으며, 이러한 노력들이 지속가능한 성장과 시장 경쟁력 강화에 기여하고 있습니다.", 
                    "21시간 전", 500, 50, 0, "twitter", "https://twitter.com/BatteryUpdate/status/5234567899"));
                break;
            default:
                tweets.add(new SnsPostDto("1", "@StockNews", 
                    stockName + " 관련 최신 뉴스가 업데이트되었습니다. 시장 분석가들은 해당 종목의 향후 전망에 대해 긍정적인 시각을 보이고 있으며, 특히 기술 혁신과 시장 확장을 통한 성장 가능성이 높다고 평가하고 있습니다. 투자자들은 이러한 긍정적 전망에 주목하고 있으며, 향후 주가 상승 여력이 충분하다는 의견이 지배적입니다.", 
                    "1시간 전", 500, 50, 0, "twitter", "https://twitter.com/StockNews/status/6234567890"));
                tweets.add(new SnsPostDto("2", "@MarketWatch", 
                    stockName + " 주가 분석 결과 현재 수준에서의 투자 기회가 있다고 판단됩니다. 기술적 분석상 주요 지지선을 유지하고 있으며, 펀더멘털 분석에서도 실적 개선과 성장 동력 확보가 예상되어 목표주가 상향 조정이 이루어지고 있습니다. 또한 배당 수익률과 PER 관점에서도 합리적인 수준을 유지하고 있어 중장기 투자 관점에서 매력적인 종목으로 평가받고 있습니다.", 
                    "3시간 전", 750, 75, 0, "twitter", "https://twitter.com/MarketWatch/status/6234567891"));
                tweets.add(new SnsPostDto("3", "@FinanceExpert", 
                    stockName + " 실적 발표를 앞두고 시장 기대감이 고조되고 있습니다. 분석가들은 매출과 영업이익 모두 전년 대비 상승할 것으로 예상하고 있으며, 특히 핵심 사업 부문에서의 성장이 두드러질 것으로 전망하고 있습니다. 또한 신규 사업 진출과 기존 사업 확장을 통한 수익성 개선도 기대되고 있어 실적 발표 후 주가 상승이 예상됩니다.", 
                    "5시간 전", 1000, 100, 0, "twitter", "https://twitter.com/FinanceExpert/status/6234567892"));
                tweets.add(new SnsPostDto("4", "@TechAnalyst", 
                    stockName + " 기술 혁신을 통해 경쟁 우위를 확보하고 있습니다. 특히 AI, 빅데이터, 클라우드 등 핵심 기술 분야에서의 R&D 투자를 확대하고 있으며, 이러한 기술 혁신이 제품 경쟁력 강화와 시장 점유율 확대로 이어지고 있습니다. 또한 디지털 전환 가속화에 따른 새로운 수요 창출에도 성공하고 있어 장기적인 성장 동력을 확보하고 있습니다.", 
                    "7시간 전", 800, 80, 0, "twitter", "https://twitter.com/TechAnalyst/status/6234567893"));
                tweets.add(new SnsPostDto("5", "@InvestorDaily", 
                    stockName + " ESG 경영을 강화하여 지속가능한 성장 모델을 구축하고 있습니다. 탄소 중립 목표 달성을 위한 친환경 경영 전환과 사회적 가치 창출을 위한 다양한 프로그램 운영에 집중하고 있으며, 지배구조 개선과 투명한 경영을 통해 기업 가치를 높이고 있습니다. 이러한 노력들이 장기적인 투자 매력도 향상과 브랜드 가치 제고에 기여하고 있습니다.", 
                    "9시간 전", 600, 60, 0, "twitter", "https://twitter.com/InvestorDaily/status/6234567894"));
                tweets.add(new SnsPostDto("6", "@BusinessNews", 
                    stockName + " 글로벌 시장 진출을 확대하여 성장 동력을 확보하고 있습니다. 특히 아시아 태평양 지역과 유럽 시장에서의 진출을 가속화하고 있으며, 현지화된 서비스 제공과 파트너십 구축을 통해 시장 점유율을 높이고 있습니다. 또한 글로벌 규제 환경 변화에 대응하여 다양한 인증을 취득하고 있으며, 이러한 노력들이 해외 시장에서의 경쟁력 강화에 기여하고 있습니다.", 
                    "11시간 전", 900, 90, 0, "twitter", "https://twitter.com/BusinessNews/status/6234567895"));
                tweets.add(new SnsPostDto("7", "@MarketAnalysis", 
                    stockName + " 업계 트렌드 변화에 따른 전략적 대응을 통해 경쟁 우위를 강화하고 있습니다. 특히 디지털 전환과 기술 혁신이 가속화되는 환경에서 선제적 투자와 사업 구조 개편을 통해 시장 변화에 대응하고 있으며, 새로운 비즈니스 모델 개발과 고객 가치 창출에 집중하고 있습니다. 이러한 전략적 접근이 시장에서의 경쟁력 강화와 지속가능한 성장에 기여하고 있습니다.", 
                    "13시간 전", 700, 70, 0, "twitter", "https://twitter.com/MarketAnalysis/status/6234567896"));
                tweets.add(new SnsPostDto("8", "@TechTrends", 
                    stockName + " 디지털 전환 가속화를 통해 새로운 비즈니스 기회를 창출하고 있습니다. 특히 클라우드, AI, IoT 등 핵심 기술을 활용한 디지털 솔루션 개발에 집중하고 있으며, 고객사의 디지털 전환을 지원하는 서비스 제공을 통해 새로운 수익원을 확보하고 있습니다. 또한 데이터 기반 의사결정과 자동화를 통한 운영 효율성 향상에도 성공하고 있어 경쟁 우위를 강화하고 있습니다.", 
                    "15시간 전", 850, 85, 0, "twitter", "https://twitter.com/TechTrends/status/6234567897"));
                tweets.add(new SnsPostDto("9", "@FinanceUpdate", 
                    stockName + " 투자를 확대하여 미래 성장성을 강화하고 있습니다. 특히 핵심 사업 부문의 R&D 투자와 신규 사업 진출을 위한 자본 투자를 늘리고 있으며, 인재 확보와 기술 개발에 집중하고 있습니다. 또한 M&A를 통한 사업 포트폴리오 확장과 전략적 파트너십 구축에도 힘쓰고 있어 장기적인 성장 동력을 확보하고 있으며, 이러한 투자가 미래 수익성 개선에 기여할 것으로 기대됩니다.", 
                    "17시간 전", 650, 65, 0, "twitter", "https://twitter.com/FinanceUpdate/status/6234567898"));
                tweets.add(new SnsPostDto("10", "@StockInsight", 
                    stockName + " 시장 점유율을 확대하여 경쟁력을 강화하고 있습니다. 특히 핵심 제품과 서비스의 품질 향상과 고객 만족도 제고를 통해 시장에서의 입지를 강화하고 있으며, 신규 고객 확보와 기존 고객과의 관계 강화에도 집중하고 있습니다. 또한 브랜드 가치 제고와 마케팅 전략 개선을 통해 시장 인지도를 높이고 있으며, 이러한 노력들이 매출 증대와 수익성 개선으로 이어지고 있습니다.", 
                    "19시간 전", 550, 55, 0, "twitter", "https://twitter.com/StockInsight/status/6234567899"));
        }
        
        return tweets;
    }
}
