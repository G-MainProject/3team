import React, { useEffect, useState } from 'react';
import styles from './Signup.module.css';
import { useNavigate } from 'react-router-dom';
import logoH from '../../assets/images/logoH.png';
import HomeNav from '../../component/Nav/HomeNav';
import Footer from '../../component/Footer/Footer';
import apiService from '../../services/api';

const Signup = () => {
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [emailId, setEmailId] = useState('');
  const [emailDomain, setEmailDomain] = useState('');
  const [emailDomainInputDisabled, setEmailDomainInputDisabled] = useState(false);
  const [selectedEmailDomainOption, setSelectedEmailDomainOption] = useState('type');
  const [email, setEmail] = useState('');
  const [id, setId] = useState('');
  const [pw, setPw] = useState('');
  const [pwRe, setPwRe] = useState('');
  const [birthday, setBirthday] = useState('');
  const [gender, setGender] = useState('');
  const [ok, setOk] = useState(1);
  const [consentAgreed, setConsentAgreed] = useState(false);

  const [pwVisible, setPwVisible] = useState(false);
  const [pwReVisible, setPwReVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [, setUsernameAvailable] = useState(null);

  const [errors, setErrors] = useState({
    id: '',
    pw: '',
    pwRe: '',
    birthday: '',
    gender: ''
  });

  const CONFIG = {
    REGEX: {
      ID: /^[a-zA-Z0-9]{6,20}$/,
      PASSWORD: /^(?=.*[A-Za-z])(?=.*[0-9])(?=.*[!@#$%^&*])[a-zA-Z0-9!@#$%^&*]{8,20}$/,
      EMAIL: /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/
    },
    ERROR_MESSAGES: {
      ID: {
        INVALID: '6~20자의 영문 소문자와 숫자만 사용 가능합니다',
        SUCCESS: '사용 가능한 아이디입니다',
        FAIL: '이미 존재하는 아이디입니다'
      },
      PASSWORD: '8~20자의 영문, 숫자, 특수문자를 모두 포함한 비밀번호를 입력해주세요',
      PASSWORD_CONFIRM: {
        SUCCESS: '비밀번호가 일치합니다',
        FAIL: '비밀번호가 일치하지 않습니다'
      },
      EMAIL: {
        INVALID: "올바른 이메일 형식이 아닙니다",
        SUCCESS: "유효한 이메일입니다"
      }
    }
  };

  // emailId, emailDomain 바뀔 때 email 상태 업데이트
  useEffect(() => {
    if (emailId && emailDomain) {
      setEmail(`${emailId}@${emailDomain}`);
    } else {
      setEmail('');
    }
  }, [emailId, emailDomain]);

  const validatePassword = pw => {
    if (CONFIG.REGEX.PASSWORD.test(pw)) {
      setErrors(prev => ({ ...prev, pw: '유효한 비밀번호입니다' }));
    } else {
      setErrors(prev => ({ ...prev, pw: CONFIG.ERROR_MESSAGES.PASSWORD }));
    }
  };

  const validatePasswordConfirm = (pw, pwRe) => {
    if (!pw || !pwRe) return;
    if (pw !== pwRe) {
      setErrors(prev => ({ ...prev, pwRe: CONFIG.ERROR_MESSAGES.PASSWORD_CONFIRM.FAIL }));
    } else {
      setErrors(prev => ({ ...prev, pwRe: CONFIG.ERROR_MESSAGES.PASSWORD_CONFIRM.SUCCESS }));
    }
  };


  // 이메일 도메인 select 변경 처리 함수
  const handleEmailDomainChange = e => {
    const val = e.target.value;
    setSelectedEmailDomainOption(val);
    if (val === 'type') {
      setEmailDomain('');
      setEmailDomainInputDisabled(false);
    } else {
      setEmailDomain(val);
      setEmailDomainInputDisabled(true);
    }
  };

  const validateEmail = (email) => {
    return CONFIG.REGEX.EMAIL.test(email);
  };


  // 아이디 중복 확인 (기존 함수 개선)
  const checkUsernameAvailability = async () => {
    if (!id) return;
    
    try {
      const response = await apiService.get(`/auth/check-username?username=${id}`);
      
      // 서버 응답: { success: true, data: true } - data가 true면 중복됨
      const isDuplicate = response.data; // response.data.data가 아니라 response.data
      setUsernameAvailable(!isDuplicate);
      
      if (isDuplicate) {
        setOk(1);
        setErrors(prev => ({ ...prev, id: CONFIG.ERROR_MESSAGES.ID.FAIL }));
      } else {
        setOk(0);
        setErrors(prev => ({ ...prev, id: CONFIG.ERROR_MESSAGES.ID.SUCCESS }));
      }
    } catch {
      setUsernameAvailable(null);
      setOk(1);
      setErrors(prev => ({ ...prev, id: '아이디 확인 중 오류가 발생했습니다' }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // 필수 필드 검사
    if (!name.trim() || !email.trim() || !id.trim() || !pw.trim() || !pwRe.trim() || !birthday.trim() || !gender.trim()) {
      setError("모든 필드를 입력해주세요.");
      setLoading(false);
      return;
    }

    // 이메일 유효성 검사
    if (!validateEmail(email)) {
      setError("올바른 이메일 형식이 아닙니다.");
      setLoading(false);
      return;
    }

    // 비밀번호 유효성 검사
    if (!CONFIG.REGEX.PASSWORD.test(pw)) {
      setError("비밀번호 형식이 올바르지 않습니다.");
      setLoading(false);
      return;
    }

    // 비밀번호 확인 검사
    if (pw !== pwRe) {
      setError("비밀번호가 일치하지 않습니다.");
      setLoading(false);
      return;
    }

    // 아이디 중복 확인 검사
    if (ok !== 0) {
      setError("아이디 중복 확인을 해주세요.");
      setLoading(false);
      return;
    }


    try {
      // 성별 값을 서버에서 기대하는 형식으로 변환
      const genderMapping = {
        'male': 'MALE',
        'female': 'FEMALE', 
        'other': 'OTHER'
      };

      const registerData = {
        email: email,
        name: name,
        gender: genderMapping[gender] || 'OTHER',
        birthDate: birthday,
        username: id,
        password: pw,
        consentAgreed: consentAgreed
      };

      const response = await apiService.post('/auth/register', registerData);
      
      
      if (response.success) {
        alert('회원가입이 성공적으로 완료되었습니다!');
        navigate('/login');
      } else {
        setError(response.message || '회원가입에 실패했습니다.');
      }
    } catch (err) {
      setError(err.response?.data?.message || '회원가입 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className={styles.signupContainer}>
      <HomeNav />
      <div className={styles.signupContent}>
        <form className={styles.signupForm}>
          <div className={styles.signupLogo}>
            <img src={logoH} alt="3Team Logo" />
          </div>

        <p>회원가입</p>
        <h1>가입을 통해 더 다양한 서비스를 만나보세요!</h1>

        <div className={styles.signupFormGroup}>
          <label htmlFor="username">이름</label>
          <input
            type="text"
            id="username"
            placeholder="이름을 입력하세요"
            onChange={e => setName(e.target.value)}
          />
        </div>

        <div className={styles.signupFormGroup}>
          <label htmlFor="email">이메일</label>
          <div className={styles.emailGroup}>
            <input
              type="text"
              placeholder="이메일 아이디"
              value={emailId}
              onChange={e => setEmailId(e.target.value)}
            />
            <p>@</p>
            <input
              className="em-box"
              id="signup-em-box"
              type="text"
              value={emailDomain}
              disabled={emailDomainInputDisabled}
              onChange={e => setEmailDomain(e.target.value)}
            />
            <select
              className="em-box"
              id="signup-em-list"
              value={selectedEmailDomainOption}
              onChange={handleEmailDomainChange}
            >
              <option value="type">직접 입력</option>
              <option value="naver.com">naver.com</option>
              <option value="gmail.com">gmail.com</option>
              <option value="hanmail.net">hanmail.net</option>
              <option value="nate.com">nate.com</option>
              <option value="kakao.com">kakao.com</option>
            </select>
          </div>
        </div>

        <div className={`${styles.signupFormGroup} id-group`}>
          <label htmlFor="id">아이디</label>
          <div className={styles.infoId}>
            <input
              type="text"
              id="id"
              placeholder="아이디를 입력하세요"
              /* 배경 클릭 시 아이디 비교 */
              // onBlur={idCompare}
              onChange={e => setId(e.target.value)}
            />
            {/* 버튼 클릭 시 아이디 비교 */}
            <button 
              className={styles.duplicateCheckBtn} 
              type="button" 
              onClick={checkUsernameAvailability}
              disabled={!id}
            >
              중복 확인
            </button>
          </div>
          <div className={styles.errorMsg}>{errors.id}</div>
        </div>

        <div className={`${styles.signupFormGroup} ${styles.infoPw}`}>
          <label htmlFor="password">비밀번호</label>
          <input
            type={pwVisible ? 'text' : 'password'}
            id="password"
            className={styles.password}
            placeholder="비밀번호를 입력하세요"
            onChange={e => {
              setPw(e.target.value);
              validatePassword(e.target.value);
              validatePasswordConfirm(e.target.value, pwRe);
            }}
          />
          <i
            className={`fa ${pwVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
            onClick={() => setPwVisible(!pwVisible)}
            style={{ cursor: 'pointer' }}
          ></i>
          <div className={styles.errorMsg}>{errors.pw}</div>
        </div>

        <div className={`${styles.signupFormGroup} ${styles.infoPwRe}`}>
          <label htmlFor="signup-rpw">패스워드 재입력</label>
          <input
            id="signup-rpw"
            className={styles.passwordRe}
            type={pwReVisible ? 'text' : 'password'}
            onChange={e => {
              setPwRe(e.target.value);
              validatePasswordConfirm(pw, e.target.value);
            }}
          />
          <i
            className={`fa ${pwReVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
            onClick={() => setPwReVisible(!pwReVisible)}
            style={{ cursor: 'pointer' }}
          ></i>
          <div className={styles.errorMsg}>{errors.pwRe}</div>
        </div>

        <div className={styles.signupFormGroup}>
          <label>성별</label>
          <div className={styles.genderGroup}>
            <button
              type="button"
              className={`${styles.genderButton} ${gender === 'male' ? styles.genderButtonActive : ''}`}
              onClick={() => setGender('male')}
            >
              남성
            </button>
            <button
              type="button"
              className={`${styles.genderButton} ${gender === 'female' ? styles.genderButtonActive : ''}`}
              onClick={() => setGender('female')}
            >
              여성
            </button>
            <button
              type="button"
              className={`${styles.genderButton} ${gender === 'other' ? styles.genderButtonActive : ''}`}
              onClick={() => setGender('other')}
            >
              밝히고 싶지 않음
            </button>
          </div>
          <div className={styles.errorMsg}>{errors.gender}</div>
        </div>

        <div className={styles.signupFormGroup}>
          <label htmlFor="birthday">생년월일</label>
          <input
            type="date"
            id="birthday"
            value={birthday}
            onChange={e => setBirthday(e.target.value)}
          />
          <div className={styles.errorMsg}>{errors.birthday}</div>
        </div>

        <div className={styles.signupFormGroup}>
          <input
            type="checkbox"
            id="consent-agree"
            checked={consentAgreed}
            onChange={e => setConsentAgreed(e.target.checked)}
          />
          <label htmlFor="consent-agree" style={{ cursor: 'pointer' }}>마케팅/이벤트 알림 수신에 동의합니다.</label>
        </div>

        {error && (
          <div className={styles.errorMessage}>
            {error}
          </div>
        )}

        <div className={`${styles.signupFormGroup} ${styles.jcc}`}>
          <button 
            type="submit" 
            className={styles.signupButton} 
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? '회원가입 중...' : '회원가입'}
          </button>
        </div>
        </form>
      </div>
      <Footer />
    </div>
  );
};

export default Signup;
