import React, { useState, useEffect } from 'react';
import styles from './Mypage.module.css';
import logoH from '../../assets/images/logoH.png';
import HomeNav from '../../component/Nav/HomeNav';
import Footer from '../../component/Footer/Footer';
import { useAuth } from '../../contexts/AuthContext';
import apiService from '../../services/api';

const Mypage = () => {
  const { user, updateUser } = useAuth();

  const [name, setName] = useState('');
  const [emailId, setEmailId] = useState('');
  const [emailDomain, setEmailDomain] = useState('');
  const [emailDomainInputDisabled, setEmailDomainInputDisabled] = useState(false);
  const [selectedEmailDomainOption, setSelectedEmailDomainOption] = useState('type');
  const [email, setEmail] = useState('');
  const [id, setId] = useState('');
  const [birthday, setBirthday] = useState('');
  const [gender, setGender] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [passwordConfirmVisible, setPasswordConfirmVisible] = useState(false);


  // 사용자 정보 초기화 (편집 모드가 아닐 때만)
  useEffect(() => {
    if (user && !isEditing) {
      setName(user.name || '');
      setId(user.username || '');
      setBirthday(user.birthDate || '');
      setGender(user.gender === 'FEMALE' ? 'female' : user.gender === 'MALE' ? 'male' : 'other');
      
      // 이메일 분리
      if (user.email) {
        const emailParts = user.email.split('@');
        if (emailParts.length === 2) {
          setEmailId(emailParts[0]);
          setEmailDomain(emailParts[1]);
          setEmail(user.email);
        }
      }
    }
  }, [user, isEditing]);

  // emailId, emailDomain 바뀔 때 email 상태 업데이트
  useEffect(() => {
    if (emailId && emailDomain) {
      setEmail(`${emailId}@${emailDomain}`);
    } else {
      setEmail('');
    }
  }, [emailId, emailDomain]);

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

  const handleEdit = () => {
    setIsEditing(true);
    setError(null);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setError(null);
    // 원래 사용자 정보로 복원
    if (user) {
      setName(user.name || '');
      setId(user.username || '');
      setBirthday(user.birthDate || '');
      setGender(user.gender === 'FEMALE' ? 'female' : user.gender === 'MALE' ? 'male' : 'other');
      setPassword('');
      setPasswordConfirm('');
      
      if (user.email) {
        const emailParts = user.email.split('@');
        if (emailParts.length === 2) {
          setEmailId(emailParts[0]);
          setEmailDomain(emailParts[1]);
          setEmail(user.email);
        }
      }
    }
  };


  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // 필수 필드 검사
    if (!name.trim() || !email.trim() || !birthday.trim() || !gender.trim()) {
      setError("모든 필드를 입력해주세요.");
      setLoading(false);
      return;
    }

    // 비밀번호가 입력된 경우에만 확인 검사
    if (password.trim() && password !== passwordConfirm) {
      setError("비밀번호가 일치하지 않습니다.");
      setLoading(false);
      return;
    }

    // 이메일 유효성 검사
    const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
    if (!emailRegex.test(email)) {
      setError("올바른 이메일 형식이 아닙니다.");
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

      const updateData = {
        email: email,
        name: name,
        gender: genderMapping[gender] || 'OTHER',
        birthDate: birthday,
        username: id
      };

      // 비밀번호가 입력된 경우에만 포함
      if (password.trim()) {
        updateData.password = password;
      }

      const response = await apiService.put(`/users/${user.id}`, updateData);
      
      console.log('정보 수정 응답:', response);
      
      if (response.success) {
        alert('정보가 성공적으로 수정되었습니다!');
        setIsEditing(false);
        
        // AuthContext의 사용자 정보 업데이트
        const updatedUser = {
          ...user,
          name: name,
          email: email,
          gender: genderMapping[gender] || 'OTHER',
          birthDate: birthday,
          username: id
        };
        updateUser(updatedUser);
      } else {
        setError(response.message || '정보 수정에 실패했습니다.');
      }
    } catch (err) {
      setError(err.response?.data?.message || '정보 수정 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className={styles.mypageContainer}>
      <HomeNav />
      <div className={styles.mypageContent}>
        <form className={styles.mypageForm}>
          <div className={styles.mypageLogo}>
            <img src={logoH} alt="3Team Logo" />
          </div>

          <p>{isEditing ? '내 정보 수정' : '내 정보'}</p>
          <h1>개인정보를 확인하고 수정할 수 있습니다!</h1>

          <div className={styles.mypageFormGroup}>
            <label htmlFor="username">이름</label>
            <input
              type="text"
              id="username"
              placeholder="이름을 입력하세요"
              value={name}
              onChange={e => setName(e.target.value)}
              disabled={!isEditing}
            />
          </div>


          <div className={styles.mypageFormGroup}>
            <label htmlFor="email">이메일</label>
            <div className={styles.emailGroup}>
              <input
                type="text"
                placeholder="이메일 아이디"
                value={emailId}
                onChange={e => setEmailId(e.target.value)}
                disabled={!isEditing}
              />
              <p>@</p>
              <input
                className="em-box"
                id="mypage-em-box"
                type="text"
                value={emailDomain}
                disabled={emailDomainInputDisabled || !isEditing}
                onChange={e => setEmailDomain(e.target.value)}
              />
              <select
                className="em-box"
                id="mypage-em-list"
                value={selectedEmailDomainOption}
                onChange={handleEmailDomainChange}
                disabled={!isEditing}
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

          <div className={styles.mypageFormGroup}>
            <label htmlFor="id">아이디</label>
            <input
              type="text"
              id="id"
              placeholder="아이디를 입력하세요"
              value={id}
              onChange={e => setId(e.target.value)}
              disabled={true}
            />
            <div className={styles.helpText}>아이디는 변경할 수 없습니다</div>
          </div>

          <div className={styles.mypageFormGroup}>
            <label>성별</label>
            <div className={styles.genderGroup}>
              <button
                type="button"
                className={`${styles.genderButton} ${gender === 'male' ? styles.genderButtonActive : ''}`}
                onClick={() => isEditing && setGender('male')}
                disabled={!isEditing}
              >
                남성
              </button>
              <button
                type="button"
                className={`${styles.genderButton} ${gender === 'female' ? styles.genderButtonActive : ''}`}
                onClick={() => isEditing && setGender('female')}
                disabled={!isEditing}
              >
                여성
              </button>
              <button
                type="button"
                className={`${styles.genderButton} ${gender === 'other' ? styles.genderButtonActive : ''}`}
                onClick={() => isEditing && setGender('other')}
                disabled={!isEditing}
              >
                밝히고 싶지 않음
              </button>
            </div>
          </div>

          <div className={styles.mypageFormGroup}>
            <label htmlFor="birthday">생년월일</label>
            <input
              type="date"
              id="birthday"
              value={birthday}
              onChange={e => setBirthday(e.target.value)}
              disabled={!isEditing}
            />
          </div>

          {isEditing && (
            <>
              <div className={`${styles.mypageFormGroup} ${styles.infoPw}`}>
                <label htmlFor="password">새 비밀번호</label>
                <input
                  type={passwordVisible ? 'text' : 'password'}
                  id="password"
                  className={styles.password}
                  placeholder="새 비밀번호를 입력하세요"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
                <i
                  className={`fa ${passwordVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                  onClick={() => setPasswordVisible(!passwordVisible)}
                  style={{ cursor: 'pointer' }}
                ></i>
                <div className={styles.helpText}>비밀번호를 변경하지 않으려면 비워두세요</div>
              </div>

              <div className={`${styles.mypageFormGroup} ${styles.infoPwRe}`}>
                <label htmlFor="passwordConfirm">비밀번호 확인</label>
                <input
                  id="passwordConfirm"
                  className={styles.passwordRe}
                  type={passwordConfirmVisible ? 'text' : 'password'}
                  placeholder="비밀번호를 다시 입력하세요"
                  value={passwordConfirm}
                  onChange={e => setPasswordConfirm(e.target.value)}
                />
                <i
                  className={`fa ${passwordConfirmVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                  onClick={() => setPasswordConfirmVisible(!passwordConfirmVisible)}
                  style={{ cursor: 'pointer' }}
                ></i>
              </div>
            </>
          )}

          {error && (
            <div className={styles.errorMessage}>
              {error}
            </div>
          )}

          <div className={`${styles.mypageFormGroup} ${styles.jcc}`}>
            {!isEditing ? (
              <button 
                type="button" 
                className={styles.editButton} 
                onClick={handleEdit}
              >
                정보 수정
              </button>
            ) : (
              <div className={styles.buttonGroup}>
                <button 
                  type="button" 
                  className={styles.cancelButton} 
                  onClick={handleCancel}
                >
                  취소
                </button>
                <button 
                  type="submit" 
                  className={styles.saveButton} 
                  onClick={handleSave}
                  disabled={loading}
                >
                  {loading ? '저장 중...' : '저장'}
                </button>
              </div>
            )}
          </div>

        </form>
      </div>
      <Footer />
    </div>
  );
};

export default Mypage;